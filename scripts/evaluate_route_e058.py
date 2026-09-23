"""Fixed E058 held-out headless cohort; no policy implementation changes."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from rsi.full import episode
from rsi.progress import compare, progress
from rsi.trace import version_manifest


SEEDS = [f'e058_holdout_{n:03}' for n in range(1, 7)]
CHARACTERS = ['Ironclad', 'Silent']
ASCENSIONS = [0, 10]
POLICIES = ['planfixed', 'planfixed_cautious_route']
CONFIGS = [dict(character=character, ascension=ascension, seed=seed, policy=policy,
                max_steps=1500, max_seconds=180)
           for seed in SEEDS for character in CHARACTERS for ascension in ASCENSIONS
           for policy in POLICIES]


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit fixed evaluation configuration before execution')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda config: episode(config, manifest), CONFIGS))
    paired = compare(results, *POLICIES)
    by_key = {(r['character'],r['seed'],r['ascension'],r['policy']): r for r in results}
    a10_outcomes = {'better': 0, 'worse': 0, 'tie': 0, 'incomplete_or_error': 0}
    for seed in SEEDS:
        for character in CHARACTERS:
            first = by_key[(character,seed,10,POLICIES[0])]
            second = by_key[(character,seed,10,POLICIES[1])]
            if first['status'] not in ('victory','normal_defeat') or second['status'] not in ('victory','normal_defeat'):
                a10_outcomes['incomplete_or_error'] += 1
            else:
                label = 'better' if progress(second)>progress(first) else 'worse' if progress(second)<progress(first) else 'tie'
                a10_outcomes[label] += 1
    affected = [r for r in results if r['policy']==POLICIES[1] and r.get('route_overrides',0)>0]
    output = {'schema_version': 1, 'experiment': 'E058', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'a10_outcomes': a10_outcomes,
              'route_overrides': sum(r.get('route_overrides',0) for r in affected),
              'affected_seeds': sorted({r['seed'] for r in affected}),
              'model_requests': 0}
    Path('experiments/E058/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'a10_outcomes': a10_outcomes, 'route_overrides': output['route_overrides'],
                      'affected_seeds': output['affected_seeds']}))


if __name__ == '__main__':
    main()
