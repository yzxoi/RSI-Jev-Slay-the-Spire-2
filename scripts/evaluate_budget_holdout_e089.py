"""E089: held-out A10 replication of the unchanged E088 budget."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.matched import MatchedJev
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = [f'e089_holdout_{number:03}' for number in range(1, 7)]
CHARACTERS = ['Ironclad', 'Silent', 'Defect', 'Regent', 'Necrobinder']
BASELINE = 'retaliate'
TREATMENT = 'retaliate_threat_budget'
CONFIGS = [
    {'character': character, 'seed': seed, 'ascension': 10, 'policy': policy,
     'max_steps': 2000, 'max_seconds': 300}
    for seed in SEEDS for character in CHARACTERS for policy in (BASELINE, TREATMENT)
]


def trace_audit(path):
    state_hash = None
    state = None
    decisions = []
    model_seconds = 0.0
    boss_entries = set()
    resource_decisions = 0
    resource_serials = []
    potion_transitions = []
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            kind, data = row['kind'], row['data']
            if kind == 'before':
                state_hash = data['state_hash']
                state = data['state']
                context = state.get('context') or {}
                if context.get('act') == 1 and str(context.get('room_type')).lower() == 'boss':
                    boss_entries.add(context.get('floor'))
            elif kind == 'selected':
                decisions.append({
                    'state_hash': state_hash,
                    'decision': state.get('decision') if state else None,
                    'context': (state or {}).get('context'),
                    'action': data['action'],
                    'name': data.get('name'),
                })
            elif kind == 'model_response':
                model_seconds += data.get('seconds') or 0.0
            elif kind == 'resource_decision':
                resource_decisions += 1
                resource_serials.append(data['combat_serial'])
            elif kind == 'potion_transition':
                potion_transitions.append(data)
    return {'decisions': decisions, 'model_seconds': round(model_seconds, 3),
            'act1_boss_entries': len(boss_entries), 'resource_decisions': resource_decisions,
            'resource_serial_unique': len(resource_serials) == len(set(resource_serials)),
            'potion_transitions': potion_transitions}


def audit_pairs(results, trace_details):
    by_key = {(r['seed'], r['character'], r['policy']): r for r in results}
    audit = []
    for seed in SEEDS:
        for character in CHARACTERS:
            baseline = by_key[seed, character, BASELINE]
            treatment = by_key[seed, character, TREATMENT]
            base = trace_details[baseline['run_id']]['decisions']
            test = trace_details[treatment['run_id']]['decisions']
            first = next((index for index in range(min(len(base), len(test)))
                          if base[index]['state_hash'] != test[index]['state_hash']
                          or base[index]['action'] != test[index]['action']), None)
            if first is None and len(base) != len(test):
                first = min(len(base), len(test))
            b = base[first] if first is not None and first < len(base) else None
            t = test[first] if first is not None and first < len(test) else None
            valid_potion_divergence = (
                b is not None and t is not None
                and b['state_hash'] == t['state_hash']
                and b['decision'] == t['decision'] == 'combat_play'
                and t['action']['action'] == 'use_potion'
                and b['action'] != t['action']
            )
            initial_same = baseline.get('initial_state_hash') == treatment.get('initial_state_hash')
            no_difference = first is None and baseline['status'] == treatment['status']
            audit.append({
                'seed': seed, 'character': character,
                'initial_state_same': initial_same,
                'first_difference_index': first,
                'first_difference_valid_potion': valid_potion_divergence if first is not None else None,
                'first_difference_state_hash': b['state_hash'] if b else None,
                'first_difference_context': b['context'] if b else None,
                'baseline_action': b['action'] if b else None,
                'treatment_action': t['action'] if t else None,
                'no_difference_identical': no_difference if first is None else None,
                'baseline_status': baseline['status'],
                'treatment_status': treatment['status'],
                'baseline_progress': [baseline.get('act'), baseline.get('floor')],
                'treatment_progress': [treatment.get('act'), treatment.get('floor')],
            })
    return audit


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    budget = Budget(max_calls=6000, max_usd=1.50, conservative_failures=True)
    jev = MatchedJev(Jev(budget))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    trace_details = {}
    for result in results:
        path = ROOT / result['trace_path']
        result['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == result['trace_sha256']
        detail = trace_audit(path)
        trace_details[result['run_id']] = detail
        result['model_seconds'] = detail['model_seconds']
        result['act1_boss_entries'] = detail['act1_boss_entries']
        result['resource_decisions'] = detail['resource_decisions']
        result['resource_serial_unique'] = detail['resource_serial_unique']
        result['verified_potion_transitions'] = sum(t['used'] for t in detail['potion_transitions'])
        result['invalid_potion_transitions'] = sum(not t['used'] for t in detail['potion_transitions'])
    paired = compare(results, BASELINE, TREATMENT)
    audit = audit_pairs(results, trace_details)
    output = {
        'schema_version': 1, 'experiment': 'E089', 'manifest': manifest,
        'configs': CONFIGS, 'results': results, 'paired': paired, 'pair_audit': audit,
        'trace_hashes_verified': sum(result['trace_verified'] for result in results),
        'budget': {'calls': budget.calls,
                   'provider_reported_cost_usd': sum(r['cost_usd'] for r in results),
                   'budgeted_spend_usd': budget.spent,
                   'uncertain_calls': budget.uncertain_calls,
                   'estimated_usd': budget.estimated_usd},
    }
    Path('experiments/E089/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'statuses': dict(Counter(result['status'] for result in results)),
        'paired': paired['outcomes'],
        'initial_state_parity': sum(a['initial_state_same'] for a in audit),
        'potion_first_divergences': sum(a['first_difference_valid_potion'] is True for a in audit),
        'invalid_first_divergences': sum(a['first_difference_valid_potion'] is False for a in audit),
        'identical_pairs': sum(a['no_difference_identical'] is True for a in audit),
        'act2_entries_by_policy': {policy: sum((r.get('act') or 0) >= 2 for r in results
                                               if r['policy'] == policy)
                                   for policy in (BASELINE, TREATMENT)},
        'trace_hashes_verified': output['trace_hashes_verified'],
        'potion_uses': sum(r['verified_potion_transitions'] for r in results if r['policy'] == TREATMENT),
        'max_one_resource_decision_per_combat': all(r['resource_serial_unique'] for r in results),
        'budget': output['budget'],
    }), flush=True)


if __name__ == '__main__':
    main()
