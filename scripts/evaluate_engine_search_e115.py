"""Pre-registered, zero-API Act 1 comparison. Never controls the visible game."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import uuid

from rsi.engine import CHARACTERS, ROOT, Headless
from rsi.engine_search import (EngineSearch, LIMITS, POLICIES, combat_boundary,
                              close_trace, extend_prefix, prefix_digest, position,
                              fresh_choices, legal_choice, macro_choice)
from rsi.resources import require_resource_interface
from rsi.teacher import select
from rsi.trace import Trace, digest, version_manifest


ORIGINAL_GAME_HASH = '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4'


def episode(config, manifest):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, **config, 'scope': 'canonical_act1', 'limits': LIMITS,
                   'policies': POLICIES, 'model_calls': 0})
    result = {**config, 'run_id': uid, 'status': 'error', 'steps': 0,
              'model_calls': 0, 'model_cost_usd': 0, 'battles_cleared': 0}
    search = EngineSearch(manifest, trace) if config['arm'] == 'search' else None
    engine = None
    state = {}
    previous = None
    scenes = Counter()
    resource_actions = Counter()
    started = time.monotonic()
    deadline = started + LIMITS['episode_seconds']
    in_combat = False
    prefix = [{'cmd': 'start_run', 'seed': config['seed'],
               'character': config['character'], 'ascension': config['ascension']}]
    key = prefix_digest(prefix)
    unchanged = 0

    def send(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Canonical episode budget exhausted')
        engine.timeout = min(30, remaining)
        return engine.send(command)

    try:
        engine = Headless(trace.directory, resource_decisions=True)
        state = send(prefix[0])
        require_resource_interface(state)
        result['initial_state_hash'] = digest(state)
        for step in range(LIMITS['episode_actions'] + 1):
            if state.get('decision') == 'game_over':
                result['status'] = 'full_victory' if state.get('victory') else 'defeat'
                break
            if position(state)[0] > 1:
                result['status'] = 'act1_clear'
                break
            if step == LIMITS['episode_actions']:
                raise TimeoutError('Canonical action cap exhausted')
            if time.monotonic() >= deadline:
                raise TimeoutError('Canonical episode budget exhausted')
            if state.get('decision') == 'combat_play':
                in_combat = True
            elif in_combat and combat_boundary(state):
                result['battles_cleared'] += 1
                in_combat = False
                if search:
                    search.cache.clear()
                    search.active_mode = None
                    search.refresh = True
            scene = state['decision']
            scenes[scene] += 1
            before = state
            before_hash = digest(before)
            evidence = None
            if in_combat:
                if search:
                    chosen, evidence, reason = search.decide(state, prefix, key, previous, deadline)
                else:
                    chosen, _, _ = select(state, POLICIES['control'], previous)
                    reason = 'control'
            else:
                chosen = macro_choice(state)
                reason = 'shared_macro'
            if legal_choice(state, chosen['action']) is None:
                raise ValueError('Canonical action not freshly legal')
            trace.write('before', {'state': state, 'state_hash': before_hash, 'prefix_hash': key})
            trace.write('candidates', fresh_choices(state))
            trace.write('decision_source', {
                'reason': reason, 'evidence': {k: evidence[k] for k in
                    ('source_trace', 'mode', 'before', 'after')} if evidence else None})
            trace.write('selected', chosen)
            state = send(chosen['action'])
            prefix.append(chosen['action'])
            key = extend_prefix(key, chosen['action'])
            after_hash = digest(state)
            trace.write('after', {'state': state, 'state_hash': after_hash})
            result['steps'] += 1
            if chosen['action']['action'] in ('use_potion', 'claim_potion_reward', 'skip_potion_reward'):
                resource_actions[chosen['action']['action']] += 1
                trace.write('resource_transition', {
                    'action': chosen['action'], 'before': before['player'].get('potions', []),
                    'after': state.get('player', {}).get('potions', [])})
            if search and in_combat:
                search.observe(before, chosen, state, evidence)
            unchanged = unchanged + 1 if before_hash == after_hash else 0
            if unchanged >= 4:
                raise RuntimeError('Four actions made no state progress')
            previous = chosen
    except TimeoutError as exc:
        result.update(status='timeout', error=str(exc))
        trace.write('failure', result['error'])
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
        trace.write('failure', result['error'])
    finally:
        if engine:
            engine.close()
            if 'forcing game_over' in (trace.directory / 'engine.stderr.log').read_text():
                result.update(status='error', error='Engine forced game_over after a stall')
    result.update(seconds=time.monotonic() - started, act=position(state)[0], floor=position(state)[1],
                  hp=state.get('player', {}).get('hp'), final_hash=digest(state),
                  final_decision=state.get('decision'), scenes=dict(scenes),
                  resource_actions=dict(resource_actions))
    if search:
        result['search'] = search.summary()
    close_trace(trace, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'search'}), flush=True)
    return result


def summarize(results):
    pairs = []
    for control, search in zip(results[::2], results[1::2]):
        if (control['character'], control['seed']) != (search['character'], search['seed']):
            raise ValueError('Unpaired results')
        valid = all(r['status'] in ('act1_clear', 'defeat') for r in (control, search))
        parity = control.get('initial_state_hash') == search.get('initial_state_hash')
        c, s = control['status'] == 'act1_clear', search['status'] == 'act1_clear'
        pairs.append({'character': control['character'], 'seed': control['seed'],
                      'control': control['status'], 'search': search['status'],
                      'initial_parity': parity,
                      'outcome': 'invalid' if not valid or not parity else
                      'better' if s > c else 'worse' if s < c else 'tie'})
    branch_errors = sum(r.get('search', {}).get('probe_error', 0) for r in results)
    mismatches = sum(r.get('search', {}).get('prediction_mismatches', 0) for r in results)
    correctness = (all(p['outcome'] != 'invalid' for p in pairs)
                   and not branch_errors and not mismatches)
    return {'pairs': pairs, 'paired_outcomes': dict(Counter(p['outcome'] for p in pairs)),
            'correctness_pass': correctness, 'branch_errors': branch_errors,
            'prediction_mismatches': mismatches,
            'arms': {arm: {'statuses': dict(Counter(r['status'] for r in results if r['arm'] == arm)),
                           'seconds': sum(r['seconds'] for r in results if r['arm'] == arm)}
                     for arm in ('control', 'search')}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=('a', 'b'), required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite an earlier iteration')
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise ValueError('Commit code before evaluation')
    if manifest['game_dll_sha256'] != ORIGINAL_GAME_HASH:
        raise ValueError('Pinned original game version mismatch')
    manifest.update(experiment='E115', cohort=args.cohort)
    configs = [dict(character=c, seed=f'e115_act1_20260929_{args.cohort}', ascension=0, arm=arm)
               for c in CHARACTERS for arm in ('control', 'search')]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda config: episode(config, manifest), configs))
    report = {'manifest': manifest, 'configs': configs, 'limits': LIMITS, 'policies': POLICIES,
              'results': results, 'summary': summarize(results), 'seconds': time.monotonic() - started}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary']), flush=True)
    if not report['summary']['correctness_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
