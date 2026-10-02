#!/usr/bin/env python3
"""Natural elite saves at three ascensions; frozen continuations precede replay."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.battle_search import baseline_choice, compact, fixture, probe
from rsi.checkpoints import continuation_path, file_hash, preflight_path, source_map
from rsi.research_restore import ENGINE_KEYS
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, manifest, write

CONFIGS = [dict(case=f'Ironclad-{suffix}-A{ascension}', character='Ironclad',
                seed=f'e132_20261002_{suffix}', ascension=ascension, index=i * 2 + j)
           for i, ascension in enumerate((0, 5, 10)) for j, suffix in enumerate('ab')]
LABELS = ('control', 'epsilon15')


class Epsilon:
    def __init__(self, case):
        self.rng = random.Random(digest([case, 'epsilon15']))

    def choose(self, state, choices, previous):
        if self.rng.random() < .15:
            return self.rng.choice(choices), 'epsilon15'
        return baseline_choice(state, previous), 'control'

    def observe(self, state):
        pass


class Budget:
    def __init__(self, used):
        self.deadline = time.monotonic() + max(0, 600 - used)

    def run(self, fn, *args, **kwargs):
        if time.monotonic() >= self.deadline:
            return {'status': 'unstarted', 'reason': 'Ten-minute batch budget exhausted'}
        return fn(*args, **kwargs)


def read_evidence(path, version):
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(path)], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL)
    data = json.loads(Path(path).read_text())
    if any(data['manifest'][k] != version[k] for k in ENGINE_KEYS):
        raise ValueError('Engine differs from frozen evidence')
    if not data['audit']['pass'] or not audit(data)['pass']:
        raise ValueError('Frozen raw evidence audit failed')
    return data


def ready(bank):
    return [f for f in bank['fixtures'] if f['status'] == 'ready' and f['room_type'] == 'Elite']


def stats(values):
    values = sorted(values)
    return {'n': len(values), 'median': statistics.median(values),
            'p95': values[math.ceil(.95 * len(values)) - 1], 'max': max(values)} if values else {}


def capture(f, version, budget):
    expected = source_map(f)
    paths, checkpoint = [], None
    for mode in ('A', 'B', 'C'):
        p = budget.run(preflight_path, f, version, mode, expected, checkpoint)
        paths.append({'mode': mode, **p})
        if mode == 'B':
            checkpoint = p.get('checkpoint')
        if p['status'] != 'match':
            break
    native_identity = False
    if checkpoint:
        save = json.loads((ROOT / checkpoint['path']).read_text())
        native_identity = save['ascension'] == f['ascension'] and save['rng']['seed'] == f['seed']
    preflight_ok = len(paths) == 3 and all(p['status'] == 'match' for p in paths) and native_identity
    references = []
    for label in LABELS:
        record = {'case': f['case'], 'label': label, 'status': 'unstarted'}
        if preflight_ok:
            battle = budget.run(probe, f, version, label, seconds=30,
                                policy=Epsilon(f['case']) if label == 'epsilon15' else None)
            record['battle'] = compact(battle)
            record['status'] = 'incomplete_reference'
            if battle['status'] in ('clear', 'defeat'):
                extended = budget.run(continuation_path, f, version, label, 'A',
                                      battle['plan'], expected, extend=True)
                record['continuation'] = extended
                record['status'] = extended['status']
        references.append(record)
    result = dict(case=f['case'], preflight=paths, native_identity_match=native_identity,
                  checkpoint=checkpoint, references=references,
                  status='match' if preflight_ok and all(r['status'] == 'match' for r in references) else 'fail')
    print(json.dumps({k: result[k] for k in ('case', 'status', 'native_identity_match')}), flush=True)
    return result


def verify(job, fixtures, version, budget):
    case, ref, checkpoint, mode = job
    frozen = fixtures[case]
    source = ref['continuation']
    result = budget.run(continuation_path, frozen, version, ref['label'], mode,
                        source['steps'], source_map(frozen), checkpoint=checkpoint)
    result.pop('steps', None)
    result.update(case=case, label=ref['label'], mode=mode,
                  full_path_match=result.get('path_hash') == source['path_hash'],
                  final_match=result.get('final_hash') == source['final_hash'])
    return result


def timing(f, checkpoint, version, budget):
    records = []
    for repeat in range(3):
        order = ('A', 'C') if (f['index'] + repeat) % 2 == 0 else ('C', 'A')
        paths = {mode: budget.run(preflight_path, f, version, mode, source_map(f), checkpoint)
                 for mode in order}
        ok = all(p['status'] == 'match' for p in paths.values())
        records.append(dict(case=f['case'], repeat=repeat, order=order, paths=paths,
                            status='match' if ok else 'fail',
                            speedup=paths['A']['restore_seconds'] / paths['C']['restore_seconds'] if ok else None))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('freeze', 'capture', 'verify'))
    parser.add_argument('--fixtures', default='experiments/E132/fixtures-v1.json')
    parser.add_argument('--references', default='experiments/E132/references-v1.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite experiment evidence')
    version = {**manifest(), 'experiment': 'E132'}
    bank = read_evidence(args.fixtures, version) if args.mode != 'freeze' else None
    refs = read_evidence(args.references, version) if args.mode == 'verify' else None
    if bank and (bank['configs'] != CONFIGS or
                 [f['case'] for f in bank['fixtures']] != [c['case'] for c in CONFIGS]):
        raise ValueError('Prespecified configs changed or disappeared')
    if refs and refs['sources']['fixtures']['sha256'] != file_hash(args.fixtures):
        raise ValueError('References belong to a different fixture bank')
    used = (refs or bank or {}).get('batch_seconds', 0)
    started = time.monotonic()
    budget = Budget(used)
    report = dict(manifest=version, configs=CONFIGS, mode=args.mode, sources={})
    if bank:
        report['sources']['fixtures'] = dict(path=args.fixtures, sha256=file_hash(args.fixtures))
        report['availability'] = [dict(case=f['case'], status=f['status'], room_type=f.get('room_type'))
                                  for f in bank['fixtures']]
    with ThreadPoolExecutor(max_workers=2) as pool:
        if args.mode == 'freeze':
            report['fixtures'] = list(pool.map(lambda c: {**c, **budget.run(fixture, c, version)}, CONFIGS))
            report['completeness_pass'] = len(ready(report)) == len(CONFIGS)
        elif args.mode == 'capture':
            report['results'] = list(pool.map(lambda f: capture(f, version, budget), ready(bank)))
            report['capture_pass'] = bool(report['results']) and all(r['status'] == 'match' for r in report['results'])
        else:
            report['sources']['references'] = dict(path=args.references, sha256=file_hash(args.references))
            fixtures = {f['case']: f for f in ready(bank)}
            expected_count = len(fixtures) * 8
            jobs = [(r['case'], ref, r['checkpoint'], mode) for r in refs['results']
                    for ref in r['references'] if ref['status'] == 'match'
                    for mode in ('B', 'C1', 'C2', 'C3')]
            report['results'] = list(pool.map(lambda j: verify(j, fixtures, version, budget), jobs))
            report['fidelity_pass'] = bool(fixtures) and refs['capture_pass'] and len(report['results']) == expected_count and all(
                r['status'] == 'match' and r['full_path_match'] and r['final_match'] for r in report['results'])
            report['fidelity_pass'] &= audit({'bank': bank, 'references': refs, 'verification': report})['pass']
            report['timing_pairs'] = []
            snapshots = {r['case']: r['checkpoint'] for r in refs['results']}
            if report['fidelity_pass']:
                groups = pool.map(lambda f: timing(f, snapshots[f['case']], version, budget), fixtures.values())
                report['timing_pairs'] = [r for group in groups for r in group]
            pairs = report['timing_pairs']
            good = len(pairs) == len(fixtures) * 3 and bool(pairs) and all(p['status'] == 'match' for p in pairs)
            report['timing'] = {mode: stats([p['paths'][mode]['restore_seconds'] for p in pairs
                                           if p['paths'][mode].get('restore_seconds') is not None]) for mode in ('A', 'C')}
            report['timing']['median_paired_speedup'] = statistics.median(p['speedup'] for p in pairs) if good else None
            report['checkpoint_files_unchanged'] = all(file_hash(ROOT / s['path']) == s['sha256']
                                                        for s in snapshots.values() if s)
            report['fidelity_pass'] &= report['checkpoint_files_unchanged']
            report['pilot_speed_pass'] = bool(good and report['timing']['median_paired_speedup'] >= 1.5 and
                                             report['timing']['C']['p95'] <= report['timing']['A']['p95'])
            report['completeness_pass'] = len(fixtures) == len(CONFIGS)
            report['entries'] = []
            if report['fidelity_pass'] and good:
                for f in fixtures.values():
                    report['entries'].append({**snapshots[f['case']], **{k: f[k] for k in
                        ('case', 'seed', 'character', 'ascension', 'prefix_hash', 'entry_hash', 'floor', 'enemies')},
                        'map_hash': digest(source_map(f)), 'engine': {k: version[k] for k in ENGINE_KEYS},
                        'allow_unpromoted': True, 'performance_promotion_pass': False,
                        'validation_scope': f'E132: {len(fixtures)} available of six configs, two continuations each; research only'})
    report['seconds'] = time.monotonic() - started
    report['batch_seconds'] = used + report['seconds']
    report['summary'] = dict(Counter(r['status'] for r in report.get('results', report.get('fixtures', []))))
    report['audit'] = audit({'bank': bank, 'references': refs, 'report': report})
    if not report['audit']['pass']:
        report['entries'] = []
        report['fidelity_pass'] = False
    write(output, report)
    print(json.dumps({k: report[k] for k in ('summary', 'batch_seconds', 'audit')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
