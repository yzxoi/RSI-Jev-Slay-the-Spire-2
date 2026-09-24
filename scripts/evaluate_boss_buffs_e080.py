"""E080 held-out paired complete-run CLI evaluation of Act 1 Boss buff use."""

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


SEEDS = [f'e080_boss_{n:03}' for n in range(1, 13)]
CHARACTERS = ['Ironclad', 'Silent']
POLICIES = ['retaliate', 'retaliate_boss_buffs']
CONFIGS = [dict(character=character, ascension=10, seed=seed, policy=policy,
                max_steps=4000, max_seconds=600)
           for seed in SEEDS for character in CHARACTERS for policy in POLICIES]


def trace_decisions(path):
    state_hash = None
    state = None
    decisions = []
    consumed = []
    for line in path.open():
        row = json.loads(line)
        if row['kind'] == 'before':
            state_hash = row['data']['state_hash']
            state = row['data']['state']
        elif row['kind'] == 'selected':
            decisions.append({'state_hash': state_hash, 'action': row['data']['action'],
                              'potion': row['data'].get('name'),
                              'context': (state or {}).get('context')})
        elif row['kind'] == 'boss_buff_transition':
            consumed.append(row['data'])
    return decisions, consumed


def pair_audit(results):
    by_key = {(r['seed'], r['character'], r['policy']): r for r in results}
    audit = []
    for seed in SEEDS:
        for character in CHARACTERS:
            baseline = by_key[seed, character, 'retaliate']
            treatment = by_key[seed, character, 'retaliate_boss_buffs']
            base_decisions, _ = trace_decisions(ROOT / baseline['trace_path'])
            test_decisions, consumed = trace_decisions(ROOT / treatment['trace_path'])
            first = next((i for i, d in enumerate(test_decisions)
                          if d['action']['action'] == 'use_potion'), None)
            before_same = (first is not None and len(base_decisions) > first
                           and all(base_decisions[i]['state_hash'] == test_decisions[i]['state_hash']
                                   and base_decisions[i]['action'] == test_decisions[i]['action']
                                   for i in range(first))
                           and base_decisions[first]['state_hash'] == test_decisions[first]['state_hash'])
            no_intervention_identical = (
                first is None and base_decisions == test_decisions
                and baseline['status'] == treatment['status']
                and baseline.get('act') == treatment.get('act')
                and baseline.get('floor') == treatment.get('floor'))
            audit.append({'seed': seed, 'character': character,
                          'initial_state_same': baseline.get('initial_state_hash') == treatment.get('initial_state_hash'),
                          'first_intervention_index': first,
                          'first_intervention_same_prefix': before_same if first is not None else None,
                          'first_intervention_state_hash': test_decisions[first]['state_hash'] if first is not None else None,
                          'boss_buff_names': [d['potion'] for d in test_decisions
                                              if d['action']['action'] == 'use_potion'],
                          'all_consumptions_verified': all(c['inventory_decreased'] for c in consumed),
                          'consumptions': consumed,
                          'no_intervention_identical': no_intervention_identical if first is None else None,
                          'baseline_status': baseline['status'], 'treatment_status': treatment['status'],
                          'baseline_progress': [baseline.get('act'), baseline.get('floor')],
                          'treatment_progress': [treatment.get('act'), treatment.get('floor')]})
    return audit


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    budget = Budget(max_calls=10000, max_usd=2.00, conservative_failures=True)
    jev = MatchedJev(Jev(budget))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    for result in results:
        path = ROOT / result['trace_path']
        result['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == result['trace_sha256']
    paired = compare(results, 'retaliate', 'retaliate_boss_buffs')
    audit = pair_audit(results)
    output = {'schema_version': 1, 'experiment': 'E080', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired, 'pair_audit': audit,
              'trace_hashes_verified': sum(r['trace_verified'] for r in results),
              'budget': {'calls': budget.calls, 'provider_cost_usd': budget.spent,
                         'uncertain_calls': budget.uncertain_calls,
                         'estimated_usd': budget.estimated_usd}}
    Path('experiments/E080/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'statuses': dict(Counter(r['status'] for r in results)),
                      'pairs': paired['outcomes'],
                      'active_pairs': sum(a['first_intervention_index'] is not None for a in audit),
                      'same_prefix_active': sum(a['first_intervention_same_prefix'] is True for a in audit),
                      'identical_inactive': sum(a['no_intervention_identical'] is True for a in audit),
                      'boss_buffs_used': sum(r.get('boss_buffs_used', 0) for r in results),
                      'trace_hashes_verified': output['trace_hashes_verified'],
                      'budget': output['budget']}), flush=True)


if __name__ == '__main__':
    main()
