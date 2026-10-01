#!/usr/bin/env python3
"""Checkpoint parity gates; outputs are immutable and every raw trace is retained."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.checkpoints import (battle_steps, continuation_path, file_hash,
                             preflight_case, source_map)
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, frozen_bank, manifest, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('preflight', 'freeze', 'verify'))
    parser.add_argument('--preflight', default='experiments/E121/preflight-v1.json')
    parser.add_argument('--bank', default='experiments/E121/continuations.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite earlier evidence')
    version = {**manifest(), 'experiment': 'E121'}
    bank = frozen_bank(ROOT / 'experiments/E120/fixtures.json')
    started = time.monotonic()
    if args.mode == 'preflight':
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda f: preflight_case(f, version), bank['fixtures']))
    else:
        preflight = json.loads(Path(args.preflight).read_text())
        if len(preflight['results']) != 10 or any(r['status'] != 'match' for r in preflight['results']):
            raise ValueError('All ten preflight cases must pass before continuation testing')
        for k in ('headless_assembly_sha256', 'headless_game_sha256', 'game_dll_sha256'):
            if preflight['manifest'][k] != version[k]:
                raise ValueError('Engine changed since preflight')
        snapshots = {r['case']: next(p['checkpoint'] for p in r['paths'] if p['mode'] == 'B')
                     for r in preflight['results']}
        fixture_by_case = {f['case']: f for f in bank['fixtures']}
        if args.mode == 'freeze':
            source = json.loads((ROOT / 'experiments/E120/results.json').read_text())
            jobs = [(fixture_by_case[r['case']], arm, r['control'] if arm == 'control'
                     else r['arms'][arm]['incumbent']) for r in source['results']
                    for arm in ('control', 'flat', 'uct')]
            def freeze_one(job):
                f, arm, record = job
                result = continuation_path(f, version, arm, 'A', battle_steps(f, record),
                                           source_map(f), extend=True)
                print(json.dumps({'case': f['case'], 'arm': arm, 'status': result['status'],
                                  'extension': result['extension_steps'], 'error': result.get('error')}), flush=True)
                return result
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(freeze_one, jobs))
        else:
            import subprocess
            import statistics
            frozen = json.loads(Path(args.bank).read_text())
            subprocess.run(['git', 'ls-files', '--error-unmatch', args.bank], check=True,
                           cwd=ROOT, stdout=subprocess.DEVNULL)
            if len(frozen['results']) != 30 or any(r['status'] != 'match' for r in frozen['results']):
                raise ValueError('Freeze all 30 passing source continuations before replay')
            for k in ('headless_assembly_sha256', 'headless_game_sha256', 'game_dll_sha256'):
                if frozen['manifest'][k] != version[k]:
                    raise ValueError('Engine changed since continuation freeze')
            jobs = [(r, mode) for r in frozen['results'] for mode in ('B', 'C1', 'C2', 'C3')]
            def verify_one(job):
                r, mode = job
                f = fixture_by_case[r['case']]
                result = continuation_path(f, version, r['label'], mode, r['steps'], source_map(f),
                                           checkpoint=snapshots[r['case']] if mode.startswith('C') else None)
                result.pop('steps')
                return result
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(verify_one, jobs))
    report = {'manifest': version, 'source_bank_hash': digest(bank), 'results': results,
              'seconds': time.monotonic() - started,
              'summary': dict(Counter(r['status'] for r in results))}
    report['audit'] = audit(report)
    if args.mode in ('freeze', 'verify'):
        report['checkpoint_manifest'] = snapshots
        report['preflight_file_sha256'] = file_hash(args.preflight)
    if args.mode == 'verify':
        reference = {(r['case'], r['label']): r for r in frozen['results']}
        comparisons = []
        for r in results:
            a = reference[r['case'], r['label']]
            comparisons.append({'case': r['case'], 'label': r['label'], 'mode': r['mode'],
                                'status': r['status'], 'full_path_match': r.get('path_hash') == a['path_hash'],
                                'final_match': r.get('final_hash') == a['final_hash'],
                                'speedup': a['restore_seconds'] / r['restore_seconds'] if r.get('restore_seconds') else None})
        report['comparisons'] = comparisons
        ratios = [r['speedup'] for r in comparisons if r['mode'].startswith('C') and r['speedup'] is not None]
        report['median_restore_speedup'] = statistics.median(ratios) if ratios else None
        report['minimum_restore_speedup'] = min(ratios) if ratios else None
        report['correctness_pass'] = all(r['status'] == 'match' and r['full_path_match'] and r['final_match'] for r in comparisons)
        report['promotion_pass'] = (len(comparisons) == 120 and report['correctness_pass'] and
                                    len(ratios) == 90 and min(ratios) >= 2 and report['audit']['pass'])
        report['source_bank_file_sha256'] = file_hash(args.bank)
    write(output, report)
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
