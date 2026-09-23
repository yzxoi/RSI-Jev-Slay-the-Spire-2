"""E062 fixed 16-pair real headless-engine comparison; no model calls."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.progress import compare
from rsi.trace import version_manifest


SEEDS = [f'e062_cap_{n:03}' for n in range(1, 5)]
CHARACTERS = ['Ironclad', 'Silent']
ASCENSIONS = [0, 10]
POLICIES = ['planfixed', 'planfixed_hitcap']
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
    paired = compare(results, 'planfixed', 'planfixed_hitcap')
    output = {'schema_version': 1, 'experiment': 'E062', 'manifest': manifest,
              'configs': CONFIGS, 'results': results, 'paired': paired,
              'hit_cap_states': sum(r.get('hit_cap_states', 0) for r in results),
              'hit_cap_choice_overrides': sum(r.get('hit_cap_choice_overrides', 0) for r in results),
              'trace_hashes_verified': sum(r['trace_verified'] for r in results),
              'model_requests': 0}
    Path('experiments/E062/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pairs': len(paired['pairs']), 'outcomes': paired['outcomes'],
                      'hit_cap_states': output['hit_cap_states'],
                      'overrides': output['hit_cap_choice_overrides'],
                      'trace_hashes_verified': output['trace_hashes_verified']}))


if __name__ == '__main__':
    main()
