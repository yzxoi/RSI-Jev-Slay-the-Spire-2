#!/usr/bin/env python3
"""Freeze legitimate battle entries, then compare zero-model search algorithms."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.battle_search import LIMITS, compact, fixture, probe, rank, search
from rsi.engine import CHARACTERS
from rsi.trace import digest, version_manifest

SEEDS = ['e120_20261001_a', 'e120_20261001_b']
CONFIGS = [dict(case=f'{character}-{suffix}', character=character, seed=seed,
                ascension=0, index=i * len(CHARACTERS) + j)
           for i, (suffix, seed) in enumerate(zip('ab', SEEDS))
           for j, character in enumerate(CHARACTERS)]
ORIGINAL_GAME = '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4'


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def manifest():
    value = version_manifest()
    if value['tracked_dirty']:
        raise ValueError('Commit all implementation changes before evaluation')
    if value['game_dll_sha256'] != ORIGINAL_GAME:
        raise ValueError('Expected historical v0.111.0 game binary')
    return {**value, 'experiment': 'E120', 'platform': platform.platform(),
            'python': platform.python_version(), 'model_calls': 0, 'model_cost_usd': 0}


def frozen_bank(path):
    bank = json.loads(Path(path).read_text())
    if bank['configs'] != CONFIGS or bank['limits'] != LIMITS:
        raise ValueError('Frozen bank protocol mismatch')
    if [r['case'] for r in bank['fixtures']] != [c['case'] for c in CONFIGS]:
        raise ValueError('Missing or reordered preselected cases')
    return bank


def evaluate_case(frozen, version, directory):
    case = frozen['case']
    result = {'case': case, 'fixture_status': frozen['status'], 'status': 'unstarted',
              'arms': {arm: {'arm': arm, 'status': 'unstarted'} for arm in ('flat', 'uct')}}
    if frozen['status'] != 'ready':
        result['status'] = 'fixture_unavailable'
    else:
        print(json.dumps({'case': case, 'phase': 'control'}), flush=True)
        control = probe(frozen, version, 'control')
        result['control'] = compact(control)
        result['status'] = 'invalid'
        if control['status'] in ('clear', 'defeat'):
            check = probe(frozen, version, 'control:verification', expected_plan=control['plan'])
            result['control_verification'] = compact(check)
            if (check['status'] == control['status'] and check['plan'] == control['plan']
                    and check.get('final_hash') == control.get('final_hash')):
                order = ('flat', 'uct') if frozen['index'] % 2 == 0 else ('uct', 'flat')
                result['arm_order'] = order
                for arm in order:
                    print(json.dumps({'case': case, 'phase': arm}), flush=True)
                    result['arms'][arm] = search(frozen, version, arm, control)
                    if result['arms'][arm]['status'] == 'invalid':
                        break
                else:
                    result['status'] = 'valid'
    write(directory / f'{case}.json', result)
    print(json.dumps({'case': case, 'status': result['status'],
                      'control': result.get('control', {}).get('status'),
                      'plans': {a: {k: v for k, v in r.get('incumbent', {}).items()
                                    if k in ('status', 'hp', 'potions')}
                                for a, r in result['arms'].items()}}), flush=True)
    return result


def summarize(results):
    rows = []
    for case in results:
        row = {'case': case['case'], 'status': case['status']}
        control = case.get('control', {})
        row['control'] = {k: control.get(k) for k in ('status', 'hp', 'potions', 'seconds')}
        for name, arm in case['arms'].items():
            best = arm.get('incumbent', {})
            row[name] = {'status': arm['status'],
                         **{k: best.get(k) for k in ('status', 'hp', 'potions')},
                         'search_status': arm['status'],
                         'simulations': arm.get('simulations'),
                         'seconds': arm.get('charged_seconds')}
        if case['status'] == 'valid':
            for weight in (0, 4, 8):
                def score(r):
                    return r['hp'] + weight * len(r['potions']) if r['status'] == 'clear' else 0
                c = score(control)
                f = score(case['arms']['flat']['incumbent'])
                u = score(case['arms']['uct']['incumbent'])
                row[f'deltas_potion_weight_{weight}'] = {'flat-control': f-c, 'uct-control': u-c,
                                                       'uct-flat': u-f}
            row['clear_statuses'] = [control['status'], case['arms']['flat']['incumbent']['status'],
                                     case['arms']['uct']['incumbent']['status']]
        rows.append(row)
    valid = [r for r in rows if r['status'] == 'valid']
    correctness = len(valid) == len(CONFIGS)
    pairs = {}
    for name in ('flat-control', 'uct-control', 'uct-flat'):
        values = [r['deltas_potion_weight_4'][name] for r in valid]
        pairs[name] = {'n': len(values), 'gains': sum(v > 0 for v in values),
                       'regressions': sum(v < 0 for v in values),
                       'ties': sum(v == 0 for v in values),
                       'median_resource_delta': statistics.median(values) if values else None}
    promote = {}
    for arm in ('flat', 'uct'):
        metrics = pairs[arm + '-control']
        no_death = all(not (r['clear_statuses'][0] == 'clear' and
                            r['clear_statuses'][1 if arm == 'flat' else 2] != 'clear') for r in valid)
        promote[arm] = bool(correctness and no_death and metrics['gains'] >= 3
                            and metrics['median_resource_delta'] >= 3)
    comparable = all(r['flat']['simulations'] == r['uct']['simulations'] == LIMITS['simulations']
                     for r in valid) and correctness
    prefer_uct = bool(comparable and pairs['uct-flat']['median_resource_delta'] > 0 and
                      pairs['uct-flat']['gains'] > pairs['uct-flat']['regressions'])
    totals = {}
    for name in ('flat', 'uct'):
        arms = [r['arms'][name] for r in results if 'probes' in r['arms'][name]]
        probes = [p for a in arms for p in a['probes']]
        seconds = sum(a['probe_seconds'] for a in arms)
        replay = sum(a['replay_seconds'] for a in arms)
        totals[name] = {'probes_including_shared_control': len(probes),
                        'probe_statuses': dict(Counter(p['status'] for p in probes)),
                        'seconds_including_shared_control': seconds,
                        'replay_seconds': replay,
                        'replay_fraction': replay / seconds if seconds else None,
                        'entry_verified': sum(p['entry_verified'] for p in probes),
                        'selection_truncations': sum(p['selection_truncations'] for p in probes)}
    return {'case_statuses': dict(Counter(r['status'] for r in results)), 'rows': rows,
            'correctness_pass': correctness, 'pairs': pairs, 'strength_gate': promote,
            'comparable_completed_budgets': comparable, 'prefer_uct_gate': prefer_uct,
            'totals': totals, 'full_runs_evaluated': 0}


def audit(report):
    """Hash all referenced raw evidence; retain duplicate control refs only once."""
    found = {}
    def walk(value):
        if isinstance(value, dict):
            if 'trace_path' in value:
                found[value['trace_path']] = value
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    walk(report)
    failures = []
    for path, record in found.items():
        full = ROOT / path
        for name, expected in [('decisions.jsonl', record['trace_sha256']),
                               ('wire.jsonl', record.get('wire.jsonl_sha256')),
                               ('engine.stderr.log', record.get('engine.stderr.log_sha256'))]:
            file = full.parent / name
            actual = hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None
            if actual != expected:
                failures.append({'path': str(file.relative_to(ROOT)), 'expected': expected, 'actual': actual})
    return {'raw_traces': len(found), 'failures': failures, 'pass': not failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('freeze', 'run', 'audit'))
    parser.add_argument('--fixtures', default='experiments/E120/fixtures.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if args.mode == 'audit':
        print(json.dumps(audit(json.loads(output.read_text())), indent=2))
        return
    if output.exists():
        raise ValueError('Do not overwrite previous evidence')
    version = manifest()
    started = time.monotonic()
    if args.mode == 'freeze':
        with ThreadPoolExecutor(max_workers=LIMITS['workers']) as pool:
            records = list(pool.map(lambda c: fixture(c, version), CONFIGS))
        report = {'manifest': version, 'configs': CONFIGS, 'limits': LIMITS, 'fixtures': records,
                  'seconds': time.monotonic() - started}
        write(output, report)
        print(json.dumps({r['case']: {k: r.get(k) for k in ('status', 'floor', 'hp', 'enemies', 'error')}
                          for r in records}, indent=2), flush=True)
    else:
        bank = frozen_bank(args.fixtures)
        subprocess.run(['git', 'ls-files', '--error-unmatch', args.fixtures], cwd=ROOT,
                       check=True, stdout=subprocess.DEVNULL)
        for key in ('game_dll_sha256', 'headless_game_sha256', 'headless_assembly_sha256'):
            if bank['manifest'][key] != version[key]:
                raise ValueError('Engine changed after fixture freeze')
        directory = output.with_suffix('')
        if directory.exists():
            raise ValueError('Partial run directory already exists; preserve it')
        directory.mkdir(parents=True)
        with ThreadPoolExecutor(max_workers=LIMITS['workers']) as pool:
            results = list(pool.map(lambda f: evaluate_case(f, version, directory), bank['fixtures']))
        report = {'manifest': version, 'fixture_bank_hash': digest(bank), 'configs': CONFIGS,
                  'fixtures': bank['fixtures'], 'limits': LIMITS, 'results': results,
                  'summary': summarize(results), 'seconds': time.monotonic() - started}
        report['audit'] = audit(report)
        write(output, report)
        print(json.dumps(report['summary'], indent=2), flush=True)


if __name__ == '__main__':
    main()
