"""Bounded teacher discovery, real-engine outcomes, independent policy repeats."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import time
import uuid

from rsi.engine import Headless, ROOT
from rsi.teacher import MODES, POTIONS, is_minion, power_amount, select, terminal
from rsi.trace import Trace, digest, version_manifest


DIRECTORY = ROOT / 'experiments/E096'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome_key(result):
    if result['status'] == 'boss_clear':
        return (2, result['final_hp'], -result['steps'])
    if result['status'] == 'boss_defeat':
        return (1, -result['remaining_leader_effective_hp'], -result['remaining_total_effective_hp'])
    return (0, 0, 0)


def battle(case, policy, label, manifest):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid, {
        **manifest, 'experiment': 'E096', 'scope': 'offline_boss_policy_search',
        'case_id': case['id'], 'policy': policy, 'label': label})
    result = {'case_id': case['id'], 'policy': policy, 'label': label,
              'status': 'error', 'run_id': uid, 'steps': 0, 'entry_verified': False}
    started = time.monotonic()
    engine = None
    state = last_combat = {}
    previous = None
    transitions = []
    used = []
    try:
        engine = Headless(trace.directory)
        for command in case['commands']:
            state = engine.send(command)
        result['entry_hash'] = digest(state)
        result['entry_verified'] = result['entry_hash'] == case['entry_hash']
        if not result['entry_verified']:
            raise RuntimeError('Frozen entry hash mismatch')
        if state.get('decision') != 'combat_play' or state.get('context', {}).get('room_type') != 'Boss':
            raise RuntimeError('Expected playable Boss entry')
        result['prefix_seconds'] = round(time.monotonic() - started, 4)
        trace.write('entry', {'state': state, 'state_hash': digest(state)})
        for step in range(301):
            status = terminal(state)
            if status:
                result['status'] = status
                break
            if step == 300 or time.monotonic() - started > 180:
                raise TimeoutError('Battle action/time budget exhausted')
            if state['decision'] == 'combat_play':
                last_combat = state
            before = digest(state)
            choice, choices, evidence = select(state, policy, previous)
            if choice not in choices:
                raise RuntimeError('Choice outside fresh candidate set')
            trace.write('before', {'state': state, 'state_hash': before})
            trace.write('candidates', choices)
            trace.write('proposal', evidence)
            trace.write('selected', choice)
            if choice['action']['action'] == 'use_potion':
                used.append({'round': state.get('round'), 'name': choice['name']})
            if state['decision'] == 'combat_play':
                previous = choice
            state = engine.send(choice['action'])
            after = digest(state)
            trace.write('after', {'state': state, 'state_hash': after})
            transitions.append([before, choice['action'], after])
            result['steps'] = step + 1
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', result['error'])
    finally:
        if engine:
            engine.close()
    enemies = last_combat.get('enemies', [])
    result.update(
        seconds=round(time.monotonic() - started, 4),
        final_hp=state.get('player', {}).get('hp'), final_decision=state.get('decision'),
        last_round=last_combat.get('round'),
        remaining_leader_effective_hp=sum(max(0, e['hp'] - power_amount(e, 'Doom'))
                                         for e in enemies if not is_minion(e)),
        remaining_total_effective_hp=sum(max(0, e['hp'] - power_amount(e, 'Doom')) for e in enemies),
        last_enemies=[{'name': e['name'], 'hp': e['hp'], 'doom': power_amount(e, 'Doom')}
                      for e in enemies],
        potions=used, trajectory_sha256=digest(transitions),
        wire_sha256=file_hash(trace.directory / 'wire.jsonl') if engine else None,
        engine_log_sha256=file_hash(trace.directory / 'engine.stderr.log') if engine else None)
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()
    result['trace_verified'] = file_hash(trace.path) == result['trace_sha256']
    return result


def initial_policies():
    return [{'mode': mode, 'loss_price': price, 'potions': potion,
             'round_modes': {}, 'selection_rank': 0}
            for price, mode, potion in itertools.product((.6, 1.5, 3.), MODES, POTIONS)]


def mutations(parents, rng):
    result = []
    for i in range(24):
        policy = copy.deepcopy(parents[i % len(parents)]['policy'])
        if i < 12:
            for _ in range(1 + i % 3):
                policy['round_modes'][str(rng.randint(1, 15))] = rng.choice(MODES)
        else:
            key = ('mode', 'loss_price', 'potions', 'selection_rank')[i % 4]
            values = {'mode': MODES, 'loss_price': (.3, .6, 1., 1.5, 2., 3., 5.),
                      'potions': POTIONS, 'selection_rank': (0, 1, 2)}[key]
            policy[key] = rng.choice(values)
        result.append(policy)
    return result


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    if manifest['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise RuntimeError('Pinned game version mismatch')
    cases = json.loads((DIRECTORY / 'fixtures.json').read_text())['cases']
    started = time.monotonic()
    results = []
    progress = ROOT / 'artifacts/runs/e096-progress.jsonl'
    progress.parent.mkdir(parents=True, exist_ok=True)
    def evaluate(jobs):
        with ThreadPoolExecutor(max_workers=4) as pool:
            batch = list(pool.map(lambda job: battle(*job, manifest=manifest), jobs))
        results.extend(batch)
        with progress.open('a') as out:
            for row in batch:
                out.write(json.dumps(row) + '\n')
        print(json.dumps({'completed': len(results), 'statuses': dict(Counter(r['status'] for r in results)),
                          'batch_clears': [r['case_id'] for r in batch if r['status'] == 'boss_clear'],
                          'errors': [r.get('error') for r in batch if r['status'] == 'error']}), flush=True)
        return batch
    # Positional job order mirrors battle(case, policy, label=..., manifest=...).
    baseline_jobs = []
    for case in cases:
        for name, potion in [('baseline', 'none'), ('early_baseline', 'early')]:
            baseline_jobs.append((case, dict(mode='legacy', loss_price=1.5, potions=potion,
                                             round_modes={}, selection_rank=0), name))
    evaluate(baseline_jobs)
    for index, case in enumerate(cases):
        batch = evaluate([(case, p, 'grid') for p in initial_policies()])
        rng = random.Random(9600 + index)
        for generation in range(3):
            if any(r['status'] == 'boss_clear' for r in results if r['case_id'] == case['id']):
                break
            parents = sorted(batch, key=outcome_key, reverse=True)[:4]
            batch += evaluate([(case, p, f'mutation_{generation}') for p in mutations(parents, rng)])
    discovery_seconds = time.monotonic() - started
    winners = []
    for case in cases:
        eligible = [r for r in results if r['case_id'] == case['id'] and r['status'] == 'boss_clear']
        if not eligible:
            continue
        selected = max(eligible, key=outcome_key)
        repeats = evaluate([(case, selected['policy'], f'repeat_{i}') for i in range(3)])
        winners.append({'case_id': case['id'], 'character': case['character'],
                        'policy': selected['policy'], 'source_run_id': selected['run_id'],
                        'final_hp': selected['final_hp'],
                        'repeat_run_ids': [r['run_id'] for r in repeats],
                        'repeatable': all(r['status'] == 'boss_clear' and
                                          r['trajectory_sha256'] == selected['trajectory_sha256']
                                          for r in repeats)})
    audit = all(r['entry_verified'] and r['trace_verified'] for r in results)
    repeatable = [w for w in winners if w['repeatable']]
    passed = audit and len(repeatable) >= 3 and any(w['character'] != 'Ironclad' for w in repeatable)
    output = dict(experiment='E096', manifest=manifest,
                  fixture_sha256=file_hash(DIRECTORY / 'fixtures.json'),
                  results=results, winners=winners, teacher_gate_passed=passed,
                  entry_and_trace_audit_passed=audit, discovery_seconds=round(discovery_seconds, 3),
                  total_seconds=round(time.monotonic() - started, 3),
                  model_calls=0, model_api_cost_usd=0,
                  limitation='Selected fixed-entry Boss development sample; no full-run or holdout claims')
    (DIRECTORY / 'result.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: output[k] for k in ('teacher_gate_passed', 'entry_and_trace_audit_passed',
                                           'discovery_seconds', 'total_seconds', 'winners')}), flush=True)


if __name__ == '__main__':
    main()
