"""E078 preregistered paired full-run test of threat-horizon potion use."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = [f'e078_potion_{n:03}' for n in range(1, 9)]
CHARACTERS = ['Ironclad', 'Silent']
ASCENSIONS = [10]
POLICIES = ['retaliate', 'retaliate_potion_horizon']
CONFIGS = [dict(character=character, ascension=ascension, seed=seed, policy=policy,
                max_steps=1500, max_seconds=180)
           for seed in SEEDS for character in CHARACTERS for ascension in ASCENSIONS
           for policy in POLICIES]


def audit_potions(path):
    before = None
    selected = None
    uses = []
    for line in path.open():
        row = json.loads(line)
        kind, data = row['kind'], row['data']
        if kind == 'before':
            before, selected = data['state'], None
        elif kind == 'selected':
            selected = data
        elif kind == 'after' and selected and selected['action']['action'] == 'use_potion':
            previous = (before or {}).get('player', {}).get('potions')
            current = data['state'].get('player', {}).get('potions')
            potion_index = selected['action']['args']['potion_index']
            original = next((p for p in previous or [] if p['index'] == potion_index), {})
            uses.append({'trace_seq': row['seq'], 'act': (before or {}).get('context', {}).get('act'),
                         'floor': (before or {}).get('context', {}).get('floor'),
                         'room_type': (before or {}).get('context', {}).get('room_type'),
                         'round': (before or {}).get('round'), 'potion': original.get('name'),
                         'potion_index': potion_index,
                         'inventory_decreased': len(current) < len(previous)
                         if current is not None and previous is not None else None})
            selected = None
    return uses


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    budget = Budget(max_calls=5000, max_usd=1.50, conservative_failures=True)
    jev = Jev(budget)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    for result in results:
        path = ROOT / result['trace_path']
        result['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == result['trace_sha256']
        result['potion_uses'] = audit_potions(path)
    paired = compare(results, 'retaliate', 'retaliate_potion_horizon')
    output = {'schema_version': 1, 'experiment': 'E078', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'trace_hashes_verified': sum(result['trace_verified'] for result in results),
              'potion_actions': sum(result.get('potion_actions', 0) for result in results
                                    if result['policy'] == 'retaliate_potion_horizon'),
              'inventory_decreases': sum(use['inventory_decreased'] is True for result in results
                                         for use in result['potion_uses']),
              'unverified_consumptions': sum(use['inventory_decreased'] is None for result in results
                                             for use in result['potion_uses']),
              'budget': {'calls': budget.calls, 'spent_usd': budget.spent,
                         'unknown_usage': budget.unknown, 'estimated_usd': budget.estimated_usd,
                         'uncertain_calls': budget.uncertain_calls}}
    Path('experiments/E078/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'potion_actions': output['potion_actions'],
                      'inventory_decreases': output['inventory_decreases'],
                      'unverified_consumptions': output['unverified_consumptions'],
                      'trace_hashes_verified': output['trace_hashes_verified'],
                      'statuses': {status: sum(r['status'] == status for r in results)
                                   for status in sorted({r['status'] for r in results})},
                      'budget': output['budget']}), flush=True)


if __name__ == '__main__':
    main()
