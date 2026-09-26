"""Frozen E103 mechanism branches; zero model or native-game calls."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time

from rsi.engine import ROOT
from rsi.end_turn_check import arithmetic, branch_plans, probe
from rsi.guard import filter_end_turn
from rsi.policy import combat_candidates
from rsi.trace import digest, version_manifest


def main():
    started = time.monotonic()
    directory = ROOT / 'experiments/E103'
    source = directory / 'inputs.json'
    inputs = json.loads(source.read_text())
    initial = ROOT / 'experiments/E099/fixtures.json'
    assert hashlib.sha256(initial.read_bytes()).hexdigest() == inputs['initial_fixtures_sha256']
    fixtures = {c['id']: c for c in json.loads(initial.read_text())['cases']}
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise ValueError('Commit before evaluation')
    if manifest['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise ValueError('Wrong game build')
    output = {'experiment': 'E103', 'scope': 'Offline mechanism comparisons, not new battle wins',
              'manifest': manifest, 'inputs_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'model_calls': 0, 'api_usd': 0, 'cases': []}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = []
        for case in inputs['cases']:
            state = case['state']
            assert digest(state) == case['entry_hash']
            prefix = fixtures[case['case']]['commands'] + case['continuation_prefix']
            nominated = branch_plans(state)
            row = {'id': case['id'], 'entry_hash': case['entry_hash'],
                   'visible_arithmetic': arithmetic(state), 'plating_arithmetic': arithmetic(state, True),
                   'legacy_guard': filter_end_turn(state, combat_candidates(state))[1],
                   'alternative_count': nominated['alternative_count'], 'truncated': nominated['truncated']}
            jobs.append((row, [pool.submit(probe, case, plan, prefix, manifest) for plan in nominated['plans']]))
        for row, pending in jobs:
            row['branches'] = [future.result() for future in pending]
            good = [b for b in row['branches'] if b['status'] != 'error']
            base = row['branches'][0]
            complete = len(good) == len(row['branches']) and not row['truncated']
            row['complete'] = complete
            if complete:
                row['best_hp_gain'] = max(b['outcome']['hp'] for b in good) - base['outcome']['hp']
                row['flags_missed_defense'] = row['best_hp_gain'] > 0
            output['cases'].append(row)
            print(json.dumps({k: v for k, v in row.items() if k in ('id', 'complete', 'best_hp_gain', 'truncated')}), flush=True)
    output['wall_seconds'] = round(time.monotonic() - started, 6)
    target = ROOT / 'artifacts/runs/e103-results.json'
    target.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'wall_seconds': output['wall_seconds'], 'branches': sum(len(c['branches']) for c in output['cases'])}))


if __name__ == '__main__':
    main()
