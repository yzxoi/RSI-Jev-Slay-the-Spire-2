"""E069 preregistered paired funded-shop relic evaluation."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = [f'e066_shop_{n:03}' for n in range(1, 4)]
CHARACTERS = ['Ironclad', 'Silent']
ASCENSIONS = [0, 10]
POLICIES = ['retaliate', 'retaliate_shop_relic']
CONFIGS = [dict(character=character, ascension=ascension, seed=seed, policy=policy,
                max_steps=1500, max_seconds=180)
           for seed in SEEDS for character in CHARACTERS for ascension in ASCENSIONS
           for policy in POLICIES]


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before evaluation')
    budget = Budget(max_calls=3000, max_usd=1.50, conservative_failures=True)
    jev = Jev(budget)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    for result in results:
        path = ROOT / result['trace_path']
        result['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == result['trace_sha256']
    paired = compare(results, 'retaliate', 'retaliate_shop_relic')
    key = lambda result: (result['character'], result['seed'], result['ascension'])
    baseline = {key(result): result for result in results if result['policy'] == 'retaliate'}
    exposed = [result for result in results if result['policy'] == 'retaliate_shop_relic'
               and result.get('shop_guard_exposures', 0) > 0]
    output = {'schema_version': 1, 'experiment': 'E069', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'trace_hashes_verified': sum(result['trace_verified'] for result in results),
              'exposed_pairs': len(exposed),
              'exposed_baseline_victories': sum(baseline[key(result)]['status'] == 'victory'
                                                for result in exposed),
              'budget': {'calls': budget.calls, 'spent_usd': budget.spent,
                         'unknown_usage': budget.unknown, 'estimated_usd': budget.estimated_usd,
                         'uncertain_calls': budget.uncertain_calls}}
    Path('experiments/E069/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'exposed_pairs': len(exposed), 'trace_hashes_verified': output['trace_hashes_verified'],
                      'statuses': {status: sum(r['status'] == status for r in results)
                                   for status in sorted({r['status'] for r in results})},
                      'budget': output['budget']}), flush=True)


if __name__ == '__main__':
    main()
