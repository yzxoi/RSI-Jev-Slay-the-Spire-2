#!/usr/bin/env python3
"""Recompute E124 accounting from recorded evidence; never invokes the game."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.battle_search import same_trajectory
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import write


def analyze(report, old, preflight):
    previous = {c['case']: c for c in old['results']}
    creation = {c['case']: next(p for p in c['paths'] if p['mode'] == 'B')
                for c in preflight['results']}
    unique, reference_paths, rows, paired = {}, set(), [], []
    for c in report['results']:
        assert c['status'] == 'valid'
        scores = {}
        for name, a in c['arms'].items():
            old_arm = previous[c['case']]['arms'][name]
            curve = next(x for x in a['curve'] if x['simulations'] == 24)
            terminal = sum(p['status'] in ('clear', 'defeat') for p in a['probes'])
            counts = dict(Counter(p['status'] for p in a['probes']))
            assert len(a['compatibility']) == 24 and all(x['match'] for x in a['compatibility'])
            assert same_trajectory(a['incumbent'], a['verification'])
            assert a['verification']['restore_mode'] == 'full_prefix'
            assert same_trajectory(curve['incumbent'], a['probes'][
                next(i for i, p in enumerate(a['probes']) if p['run_id'] == curve['incumbent']['run_id'])])
            assert curve['incumbent']['path_hash'] == old_arm['incumbent']['path_hash']
            assert curve['incumbent']['final_hash'] == old_arm['incumbent']['final_hash']
            for p in a['probes']:
                unique[p['trace_path']] = p
            reference_paths.update(p['trace_path'] for p in a['probes'][:24])
            snapshot = creation[c['case']]
            rows.append({'case': c['case'], 'arm': name, 'attempts': a['simulations'],
                         'completed_terminal_rollouts': terminal, 'probe_statuses': counts,
                         'old_24_seconds': old_arm['charged_seconds'],
                         'checkpoint_24_seconds': curve['charged_seconds'],
                         'same_24_speedup': old_arm['charged_seconds'] / curve['charged_seconds'],
                         'final_search_seconds': a['charged_seconds'],
                         'final_verification_seconds': a['verification']['seconds'],
                         'snapshot_full_build_seconds': snapshot['seconds'],
                         'snapshot_save_command_seconds': snapshot['save_seconds'],
                         'build_seconds_per_completed_rollout_single_arm': snapshot['seconds'] / terminal,
                         'save_seconds_per_completed_rollout_single_arm': snapshot['save_seconds'] / terminal,
                         'replay_fraction': a['replay_seconds'] / a['probe_seconds'],
                         'best_probe': a['incumbent']['label'],
                         'hp_at_24': curve['incumbent']['hp'], 'hp_at_final': a['incumbent']['hp']})
            p = a['incumbent']
            scores[name] = p['hp'] + 4 * len(p['potions']) if p['status'] == 'clear' else 0
        paired.append({'case': c['case'], 'uct_minus_flat': scores['uct'] - scores['flat'],
                       'equal_completed_rollouts': rows[-1]['completed_terminal_rollouts'] ==
                                                   rows[-2]['completed_terminal_rollouts']})
    deltas = [p['uct_minus_flat'] for p in paired]
    equal = all(p['equal_completed_rollouts'] for p in paired)
    arms = {}
    for name in ('flat', 'uct'):
        rr = [r for r in rows if r['arm'] == name]
        arms[name] = {'charged_attempts': sum(r['attempts'] for r in rr),
                      'charged_terminal_rollouts': sum(r['completed_terminal_rollouts'] for r in rr),
                      'median_same_24_speedup': statistics.median(r['same_24_speedup'] for r in rr),
                      'median_checkpoint_24_seconds': statistics.median(r['checkpoint_24_seconds'] for r in rr),
                      'median_old_24_seconds': statistics.median(r['old_24_seconds'] for r in rr),
                      'median_terminal_rollouts': statistics.median(r['completed_terminal_rollouts'] for r in rr),
                      'median_build_amortization_seconds': statistics.median(
                          r['build_seconds_per_completed_rollout_single_arm'] for r in rr)}
    return {'rows': rows, 'arms': arms, 'paired': paired,
            'compatibility_charged': 24 * len(rows), 'compatibility_unique': len(reference_paths),
            'unique_search_attempts': len(unique),
            'unique_probe_statuses': dict(Counter(p['status'] for p in unique.values())),
            'full_prefix_final_verifications': len(rows),
            'verification_seconds_total': sum(r['final_verification_seconds'] for r in rows),
            'uct_minus_flat': {'gains': sum(d > 0 for d in deltas), 'ties': sum(d == 0 for d in deltas),
                               'regressions': sum(d < 0 for d in deltas),
                               'median': statistics.median(deltas), 'mean': statistics.mean(deltas)},
            'equal_completed_budgets': equal,
            'prefer_uct_gate': equal and statistics.median(deltas) > 0 and
                               sum(d > 0 for d in deltas) > sum(d < 0 for d in deltas),
            'accounting_notes': [
                'Shared control charged to both arms, deduplicated in unique_search_attempts.',
                'Timeouts are censored incomplete probes, not losses or transition errors.',
                'Old E120 arms stopped at 24 probes before the same 120-second ceiling: final-quality comparison changes actual work and elapsed time.',
                'Independent final verification is excluded from search time and reported separately.',
                'Historical E121 snapshot creation is excluded from E124 execution; full build includes prefix replay, entry and teardown. Save-command time is the incremental cost at an existing map.',
                'Amortization conservatively charges the entire snapshot build to each single arm; the experiment actually shares one existing snapshot across both arms.',
                'No clear regressions is partly guaranteed by retaining the control incumbent, not independent proof of strategy safety.'
            ]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='artifacts/runs/e124-v1.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    paths = {'e124': Path(args.input), 'e120': ROOT / 'experiments/E120/results.json',
             'e121_preflight': ROOT / 'experiments/E121/preflight-v1.json'}
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite previous evidence')
    result = analyze(*(json.loads(paths[k].read_text()) for k in ('e124', 'e120', 'e121_preflight')))
    result['sources'] = {k: {'path': str(p), 'sha256': file_hash(p)} for k, p in paths.items()}
    write(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'accounting_notes')}, indent=2))


if __name__ == '__main__':
    main()
