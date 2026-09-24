"""Replay two frozen Boss entries and compare bound potion openings."""

import hashlib
import json
from pathlib import Path
import time
import uuid

from rsi.engine import Headless, ROOT
from rsi.full import STRATEGY, fixed_macro, macro_candidates
from rsi.jev import Budget, Jev
from rsi.matched import MatchedJev
from rsi.planner import choose_plan
from rsi.policy import combat_candidates, model_state
from rsi.potions import with_potions
from rsi.trace import Trace, digest, version_manifest


FIXTURE = ROOT / 'experiments/E079/frozen-boss-prefixes.json'
OUTPUT = ROOT / 'experiments/E079/result.json'


def run_branch(case, arm, manifest, jev, fixture_hash):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, 'experiment': 'E079', 'scope': 'one_boss_from_exact_prefix',
                   'seed': case['seed'], 'arm': arm, 'fixture_sha256': fixture_hash})
    result = {'character': case['character'], 'ascension': case['ascension'],
              'seed': case['seed'], 'arm': arm, 'run_id': uid, 'status': 'error',
              'expected_entry_hash': case['expected_boss_entry_state_sha256'],
              'prefix_command_count': case['prefix_command_count'],
              'prefix_commands_replayed': 0, 'boss_decisions': 0,
              'model_calls': 0, 'cache_hits': 0, 'model_cost_usd': 0.0,
              'planned_potions': case['plan_potions_in_order'] if arm == 'treatment' else [],
              'consumed_potions': []}
    engine = None
    state = {}
    last_combat = {}
    history = {}
    started = time.monotonic()
    try:
        engine = Headless(trace.directory)
        for command in case['prefix_commands']:
            state = engine.send(command)
            result['prefix_commands_replayed'] += 1
        result['entry_hash'] = digest(state)
        trace.write('boss_entry', {'state_hash': result['entry_hash'], 'state': state})
        if result['entry_hash'] != result['expected_entry_hash']:
            raise RuntimeError('Exact frozen Boss-entry state mismatch')
        if state.get('decision') != 'combat_play' or state.get('context', {}).get('room_type') != 'Boss':
            raise RuntimeError('Frozen entry is not a playable Boss state')
        result['entry_hp'] = state['player']['hp']
        result['entry_enemy_hp'] = {str(e['index']): e['hp'] for e in state.get('enemies', [])}
        result['entry_potions'] = [p['name'] for p in state['player'].get('potions', [])]

        if arm == 'treatment':
            for name in case['plan_potions_in_order']:
                if state.get('decision') != 'combat_play' or state.get('round') != 1:
                    raise RuntimeError(f'Boss opening changed before planned potion {name}')
                options = with_potions(state, [])
                selected = next((c for c in options if c['name'] == name), None)
                if selected is None:
                    raise RuntimeError(f'Planned potion is not legal: {name}')
                before_inventory = state['player']['potions']
                trace.write('before', {'state_hash': digest(state), 'state': state})
                trace.write('candidates', options)
                trace.write('selected', selected)
                state = engine.send(selected['action'])
                trace.write('after', {'state_hash': digest(state), 'state': state})
                after_inventory = state.get('player', {}).get('potions')
                consumed = (after_inventory is not None
                            and len(after_inventory) == len(before_inventory) - 1)
                result['consumed_potions'].append({'name': name, 'inventory_decreased': consumed,
                                                   'round': 1})
                if not consumed:
                    raise RuntimeError(f'Potion inventory did not decrease after {name}')

        for step in range(300):
            if time.monotonic() - started > 180:
                raise TimeoutError('Boss-branch time budget exhausted')
            decision = state.get('decision')
            if decision == 'game_over':
                result['status'] = 'boss_defeat'
                break
            if decision not in ('combat_play', 'card_select'):
                result['status'] = 'boss_cleared'
                break
            result['boss_decisions'] = step + 1
            trace.write('before', {'state_hash': digest(state), 'state': state})
            if decision == 'combat_play':
                last_combat = state
                choices = combat_candidates(state)
                selected, planning = choose_plan(state, choices, triggers=True, retaliation=True)
                trace.write('planning', planning)
            else:
                choices = macro_candidates(state, history)
                if len(choices) == 1:
                    selected = fixed_macro(state, choices)
                else:
                    selected, meta = jev.choose({'state': model_state(state), 'strategy': STRATEGY,
                                                 'previous_decision': history.get('previous')},
                                                choices, trace)
                    result['model_calls'] += not meta.get('cache_hit', False)
                    result['cache_hits'] += bool(meta.get('cache_hit', False))
                    result['model_cost_usd'] += meta['usage'].get('cost', 0)
            trace.write('candidates', choices)
            trace.write('selected', selected)
            if decision != 'card_select':
                history['previous'] = {'scene': decision, 'choice': selected}
            state = engine.send(selected['action'])
            trace.write('after', {'state_hash': digest(state), 'state': state})
        else:
            raise TimeoutError('Boss-branch decision budget exhausted')
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', {'error': result['error']})
    finally:
        if engine:
            engine.close()
            wire = trace.directory / 'wire.jsonl'
            result['wire_sha256'] = hashlib.sha256(wire.read_bytes()).hexdigest()
            result['engine_log_sha256'] = hashlib.sha256(
                (trace.directory / 'engine.stderr.log').read_bytes()).hexdigest()
    result['seconds'] = round(time.monotonic() - started, 3)
    result['final_decision'] = state.get('decision')
    result['final_hp'] = state.get('player', {}).get('hp')
    result['boss_rounds'] = last_combat.get('round')
    result['enemy_hp_at_last_combat'] = {
        str(e['index']): e['hp'] for e in last_combat.get('enemies', [])}
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()
    print(json.dumps({k: result.get(k) for k in
                      ['character', 'seed', 'arm', 'status', 'error', 'prefix_commands_replayed',
                       'entry_hash', 'consumed_potions', 'boss_rounds', 'final_hp',
                       'enemy_hp_at_last_combat', 'model_calls', 'cache_hits', 'seconds']},
                     ensure_ascii=False), flush=True)
    return result


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    fixture_bytes = FIXTURE.read_bytes()
    fixture = json.loads(fixture_bytes)
    budget = Budget(max_calls=100, max_usd=.10, conservative_failures=True)
    jev = MatchedJev(Jev(budget))
    results = [run_branch(case, arm, manifest, jev, hashlib.sha256(fixture_bytes).hexdigest())
               for case in fixture['cases'] for arm in ('baseline', 'treatment')]
    for result in results:
        result['trace_verified'] = hashlib.sha256(
            (ROOT / result['trace_path']).read_bytes()).hexdigest() == result['trace_sha256']
    output = {'schema_version': 1, 'experiment': 'E079', 'manifest': manifest,
              'fixture_sha256': hashlib.sha256(fixture_bytes).hexdigest(),
              'results': results, 'trace_hashes_verified': sum(r['trace_verified'] for r in results),
              'budget': {'calls': budget.calls, 'provider_cost_usd': budget.spent,
                         'uncertain_calls': budget.uncertain_calls,
                         'estimated_usd': budget.estimated_usd}}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'statuses': [r['status'] for r in results],
                      'entry_parity': [r.get('entry_hash') == r['expected_entry_hash'] for r in results],
                      'trace_hashes_verified': output['trace_hashes_verified'],
                      'budget': output['budget']}), flush=True)


if __name__ == '__main__':
    main()
