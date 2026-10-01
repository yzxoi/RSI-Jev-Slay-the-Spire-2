#!/usr/bin/env python3
"""Bounded research experiment; does not promote E121's failed speed gates."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.battle_search import LIMITS, compact, probe, same_trajectory, search
from rsi.checkpoints import battle_steps, file_hash
from rsi.research_restore import research_snapshots
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, frozen_bank, manifest, write

BUDGET = {**LIMITS, 'simulations': 64}


def reference_records(frozen, source):
    cache = {}
    def transform(record):
        key = record['trace_path']
        if key not in cache:
            cache[key] = {k: record[k] for k in ('status', 'path_hash', 'final_hash', 'steps')}
            cache[key]['transition_hash'] = digest(battle_steps(frozen, record))
        return cache[key]
    return {a: [transform(p) for p in source['arms'][a]['probes']] for a in ('flat', 'uct')}


def case(frozen, source, snapshot, version, directory):
    result = {'case': frozen['case'], 'status': 'invalid',
              'arms': {a: {'arm': a, 'status': 'unstarted'} for a in ('flat', 'uct')}}
    refs = reference_records(frozen, source)
    control = probe(frozen, version, 'control', checkpoint=snapshot)
    result['control'] = compact(control)
    result['control_compatibility'] = same_trajectory(control, refs['flat'][0])
    if result['control_compatibility']:
        order = ('flat', 'uct') if frozen['index'] % 2 == 0 else ('uct', 'flat')
        result['arm_order'] = order
        for arm in order:
            result['arms'][arm] = search(frozen, version, arm, control, search_limits=BUDGET,
                                        checkpoint=snapshot, reference=refs[arm])
            if result['arms'][arm]['status'] == 'invalid' or not result['arms'][arm]['compatibility_pass']:
                break
        else:
            result['status'] = 'valid'
    write(directory / (frozen['case'] + '.json'), result)
    print(json.dumps({'case': result['case'], 'status': result['status'], 'plans': {
        a: {k: v.get('incumbent', {}).get(k) for k in ('status', 'hp')} for a, v in result['arms'].items()}}), flush=True)
    return result


def summarize(results, previous):
    rows = []
    for r in results:
        row = {'case': r['case'], 'status': r['status'], 'arms': {}}
        for name, a in r['arms'].items():
            old = previous[r['case']]['arms'][name]
            b, p = a.get('incumbent', {}), old['incumbent']
            row['arms'][name] = {'status': a['status'], 'old_status': p['status'], 'new_status': b.get('status'),
                                 'old_hp': p['hp'], 'new_hp': b.get('hp'), 'old_potions': p['potions'],
                                 'new_potions': b.get('potions'), 'simulations': a.get('simulations'),
                                 'old_seconds': old['charged_seconds'], 'seconds': a.get('charged_seconds'),
                                 'depth': a.get('tree', {}).get('max_tree_depth'),
                                 'compatibility': a.get('compatibility_pass'),
                                 'score_delta': ((b['hp'] + 4*len(b['potions']) if b['status']=='clear' else 0) -
                                                 (p['hp'] + 4*len(p['potions']) if p['status']=='clear' else 0)) if b else None}
        rows.append(row)
    valid = len(results) == 10 and all(r['status'] == 'valid' for r in results)
    arms = {}
    for name in ('flat', 'uct'):
        available = [r['arms'][name] for r in rows if r['status'] == 'valid'
                     and r['arms'][name]['score_delta'] is not None]
        deltas = [a['score_delta'] for a in available]
        clears = sum(a['new_status']=='clear' for a in available)
        median = statistics.median(deltas) if deltas else None
        regressions = sum(a['old_status']=='clear' and a['new_status']!='clear' for a in available)
        arms[name] = {'n':len(available), 'clears':clears, 'gains':sum(d>0 for d in deltas),
                      'resource_regressions':sum(d<0 for d in deltas), 'clear_regressions':regressions,
                      'median_delta': median, 'mean_delta':statistics.mean(deltas) if deltas else None,
                      'median_seconds':statistics.median(a['seconds'] for a in available) if available else None,
                      'median_simulations':statistics.median(a['simulations'] for a in available) if available else None,
                      'expanded_budget_promising':bool(valid and not regressions and (clears>9 or
                           (sum(d>0 for d in deltas)>=3 and median>=3)))}
    return {'case_statuses':dict(Counter(r['status'] for r in results)), 'correctness_pass':valid,
            'rows':rows, 'arms':arms, 'full_runs_evaluated':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--allow-unpromoted-checkpoints', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    directory = output.with_suffix('')
    if output.exists() or directory.exists():
        raise ValueError('Preserve previous/partial runs')
    version = {**manifest(), 'experiment':'E124', 'search_limits':BUDGET,
               'checkpoint_performance_promoted':False, 'research_opt_in':args.allow_unpromoted_checkpoints}
    bank = frozen_bank(ROOT / 'experiments/E120/fixtures.json')
    index_path = ROOT / 'experiments/E121/verified-checkpoints.json'
    snapshots = research_snapshots(index_path, version, allow_unpromoted=args.allow_unpromoted_checkpoints)
    old = json.loads((ROOT / 'experiments/E120/results.json').read_text())
    previous = {r['case']:r for r in old['results']}
    directory.mkdir(parents=True)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda f:case(f, previous[f['case']], snapshots[f['case']], version, directory), bank['fixtures']))
    report = {'manifest':version,'checkpoint_index_sha256':file_hash(index_path),
              'e120_results_sha256':file_hash(ROOT / 'experiments/E120/results.json'),
              'results':results,'seconds':time.monotonic()-started,'summary':summarize(results,previous)}
    report['audit']=audit(report)
    write(output, report)
    print(json.dumps(report['summary'],indent=2),flush=True)


if __name__=='__main__':
    main()
