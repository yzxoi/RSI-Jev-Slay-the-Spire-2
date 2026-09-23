"""E057 fixed-cohort, actual headless-engine paired evaluation."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from rsi.full import episode
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = [f'e057_route_{n:03}' for n in range(1, 4)]
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
        raise RuntimeError('Commit implementation before evaluation')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda config: episode(config, manifest), CONFIGS))
    paired = compare(results, 'planfixed', 'planfixed_cautious_route')
    # The generic comparison omits ascension in its detail object; recompute
    # it directly from keyed complete results for a transparent A10 tally.
    by_key = {(r['character'],r['seed'],r['ascension'],r['policy']): r for r in results}
    a10_outcomes = {'better': 0, 'worse': 0, 'tie': 0, 'incomplete_or_error': 0}
    from rsi.progress import progress
    for seed in SEEDS:
        for character in CHARACTERS:
            first = by_key[(character,seed,10,'planfixed')]
            second = by_key[(character,seed,10,'planfixed_cautious_route')]
            if first['status'] not in ('victory','normal_defeat') or second['status'] not in ('victory','normal_defeat'):
                a10_outcomes['incomplete_or_error'] += 1
            else:
                a10_outcomes['better' if progress(second)>progress(first) else 'worse' if progress(second)<progress(first) else 'tie'] += 1
    output = {'schema_version': 1, 'experiment': 'E057', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'a10_outcomes': a10_outcomes,
              'route_overrides': sum(r.get('route_overrides',0) for r in results if r['policy']=='planfixed_cautious_route'),
              'model_requests': 0}
    Path('experiments/E057/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'a10_outcomes': a10_outcomes, 'route_overrides': output['route_overrides']}))


if __name__ == '__main__':
    main()
