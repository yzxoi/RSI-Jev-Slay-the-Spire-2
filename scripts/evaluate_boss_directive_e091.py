"""Paired exact-entry replay: free-text Astra plan versus typed opening directives."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.matched import MatchedJev
from rsi.trace import digest, version_manifest


FIXTURE_PATH = Path('experiments/E090/fixtures.json')
PLANS_PATH = Path('experiments/E091/plans.json')
CONTROL_PATH = Path('experiments/E090/plans.json')
FIXTURE = json.loads(FIXTURE_PATH.read_text())
PLANS = json.loads(PLANS_PATH.read_text())
CONTROL = json.loads(CONTROL_PATH.read_text())
assert PLANS['schema_version'] == 1
PLANS_BY_CASE = {plan['case_id']: plan for plan in PLANS['plans']}
CONTROL_BY_CASE = {plan['case_id']: plan for plan in CONTROL['plans']}
assert len(PLANS_BY_CASE) == len(PLANS['plans']) == len(FIXTURE['cases'])
CONFIGS = [
    {'case_id': case['id'], 'arm': arm, 'character': case['character'],
     'seed': case['seed'], 'ascension': case['ascension'],
     'policy': 'retaliate_boss_plan' if arm == 'control' else 'retaliate_boss_directive',
     'max_steps': 2000, 'max_seconds': 300,
     'replay_prefix_actions': case['prefix_actions'],
     'expected_entry_hash': case['entry_state_hash'],
     'stop_after_boss_room': True,
     'astra_boss_plan': (CONTROL_BY_CASE[case['id']] if arm == 'control' else PLANS_BY_CASE[case['id']])}
    for case in FIXTURE['cases'] for arm in ('control', 'treatment')
]


def trace_audit(path, case, arm):
    entry = []
    plans = []
    plan_decisions = []
    boundaries = []
    directives = []
    potion_transitions = []
    before_state = None
    candidates = None
    all_selected_legal = True
    max_round = 0
    last_enemy_hp = None
    for line in path.open(encoding='utf-8'):
        row = json.loads(line)
        kind, data = row['kind'], row['data']
        if kind == 'replay_entry':
            entry.append(data)
        elif kind == 'astra_boss_plan':
            plans.append(data)
        elif kind == 'before':
            before_state = data['state']
            context = before_state.get('context') or {}
            if (context.get('act'), context.get('floor'), context.get('room_type')) == (1, case['floor'], 'Boss'):
                max_round = max(max_round, before_state.get('round') or 0)
                last_enemy_hp = sum(enemy.get('hp', 0) for enemy in before_state.get('enemies', []))
        elif kind == 'candidates':
            candidates = data
        elif kind == 'selected':
            all_selected_legal &= bool(candidates and data['action'] in [c['action'] for c in candidates])
        elif kind == 'astra_boss_decision':
            context = (before_state or {}).get('context') or {}
            plan_decisions.append({'state_hash': data['state_hash'],
                                   'round': (before_state or {}).get('round'),
                                   'in_scope': (context.get('act'), context.get('floor'), context.get('room_type'))
                                    == (1, case['floor'], 'Boss'),
                                   'duplicator_followup': data['duplicator_followup'],
                                   'action': data['choice']['action']})
        elif kind == 'astra_boss_directive':
            context = (before_state or {}).get('context') or {}
            directives.append({**data,
                'state_verified': data['state_hash'] == digest(before_state),
                'in_scope': (context.get('act'), context.get('floor'), context.get('room_type'))
                    == (1, case['floor'], 'Boss')})
        elif kind == 'potion_transition':
            potion_transitions.append(data)
        elif kind == 'boss_room_boundary':
            boundaries.append(data)
    return {
        'entry_verified': len(entry) == 1 and entry[0]['state_hash'] == case['entry_state_hash'],
        'plan_verified': len(plans) == 1 and plans[0] == (PLANS_BY_CASE[case['id']] if arm == 'treatment' else CONTROL_BY_CASE[case['id']]),
        'plan_decisions': plan_decisions,
        'plan_exposed': bool(plan_decisions),
        'directives': directives,
        'directives_verified': (([d['directive'] for d in directives] == PLANS_BY_CASE[case['id']]['opening_actions']
                                 and [d['index'] for d in directives] == list(range(len(directives)))
                                 and all(d['state_verified'] and d['in_scope'] for d in directives))
                                if arm == 'treatment' else not directives),
        'plan_scope_valid': all(d['in_scope'] for d in plan_decisions),
        'all_selected_legal': all_selected_legal,
        'potion_transitions_valid': all(t['used'] for t in potion_transitions),
        'potion_uses': len(potion_transitions),
        'potion_budget_valid': len(potion_transitions) <= (PLANS_BY_CASE[case['id']]['max_potions'] if arm == 'treatment' else CONTROL_BY_CASE[case['id']]['max_potions']),
        'boundary_verified': len(boundaries) == 1,
        'boundary': boundaries[0] if boundaries else None,
        'max_round': max_round,
        'last_enemy_hp': last_enemy_hp,
    }


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation, fixtures and plans before evaluation')
    budget = Budget(max_calls=1000, max_usd=.50, conservative_failures=True)
    jev = MatchedJev(Jev(budget))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    case_by_id = {case['id']: case for case in FIXTURE['cases']}
    by_key = {(run['case_id'], run['arm']): run for run in results}
    for run in results:
        path = ROOT / run['trace_path']
        run['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == run['trace_sha256']
        audit = trace_audit(path, case_by_id[run['case_id']], run['arm'])
        run.update(audit)
        run['prefix_action_count'] = len(run.pop('replay_prefix_actions'))
        run.pop('astra_boss_plan')
    pairs = []
    for case in FIXTURE['cases']:
        baseline = by_key[case['id'], 'control']
        treatment = by_key[case['id'], 'treatment']
        pairs.append({'case_id': case['id'], 'character': case['character'],
                      'boss': case['boss_name'],
                      'control_status': baseline['status'],
                      'treatment_status': treatment['status'],
                      'control_cleared': bool(baseline.get('boss_cleared')),
                      'treatment_cleared': bool(treatment.get('boss_cleared')),
                      'control_max_round': baseline['max_round'],
                      'treatment_max_round': treatment['max_round'],
                      'control_last_enemy_hp': baseline['last_enemy_hp'],
                      'treatment_last_enemy_hp': treatment['last_enemy_hp'],
                      'treatment_potion_uses': treatment['potion_uses']})
    output = {'schema_version': 1, 'experiment': 'E091', 'manifest': manifest,
              'fixture_sha256': hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
              'plans_sha256': hashlib.sha256(PLANS_PATH.read_bytes()).hexdigest(),
              'control_plans_sha256': hashlib.sha256(CONTROL_PATH.read_bytes()).hexdigest(),
              'configs': [{k: v for k, v in config.items()
                           if k not in ('replay_prefix_actions', 'astra_boss_plan')}
                          for config in CONFIGS],
              'results': results, 'pairs': pairs,
              'trace_hashes_verified': sum(run['trace_verified'] for run in results),
              'budget': {'attempted_calls': budget.calls,
                         'provider_reported_cost_usd': sum(run['cost_usd'] for run in results),
                         'budgeted_spend_usd': budget.spent,
                         'uncertain_calls': budget.uncertain_calls,
                         'estimated_unknown_usd': budget.estimated_usd}}
    Path('experiments/E091/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'statuses': dict(Counter(run['status'] for run in results)),
                      'entry_verified': sum(run['entry_verified'] for run in results),
                      'plan_verified': sum(run['plan_verified'] for run in results),
                      'plan_exposed': sum(run['plan_exposed'] for run in results),
                      'selected_legal': sum(run['all_selected_legal'] for run in results),
                      'plan_scope_valid': sum(run['plan_scope_valid'] for run in results),
                      'potion_budget_valid': sum(run['potion_budget_valid'] for run in results),
                      'boundary_verified': sum(run['boundary_verified'] for run in results),
                      'trace_hashes_verified': output['trace_hashes_verified'],
                      'control_clears': sum(p['control_cleared'] for p in pairs),
                      'directives_verified': sum(run['directives_verified'] for run in results),
                      'treatment_clears': sum(p['treatment_cleared'] for p in pairs),
                      'pairs': pairs, 'budget': output['budget']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
