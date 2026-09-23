"""E063 fixed 20-pair Letter Opener headless-engine comparison."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = ['e062_cap_003'] + [f'e063_letter_{n:03}' for n in range(1, 5)]
CHARACTERS = ['Ironclad', 'Silent']
ASCENSIONS = [0, 10]
POLICIES = ['planfixed', 'planfixed_letter']
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
    for result in results:
        path = ROOT / result['trace_path']
        result['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == result['trace_sha256']
    paired = compare(results, 'planfixed', 'planfixed_letter')
    output = {'schema_version': 1, 'experiment': 'E063', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'trace_hashes_verified': sum(r['trace_verified'] for r in results),
              'model_requests': 0}
    Path('experiments/E063/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'trace_hashes_verified': output['trace_hashes_verified']}))


if __name__ == '__main__':
    main()
