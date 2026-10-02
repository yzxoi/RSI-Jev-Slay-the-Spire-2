#!/usr/bin/env python3
"""Offline E125 accounting; keep censored initial-policy outcomes unscored."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import audit, write


def behaviors(records):
    actions, decisions = Counter(), Counter()
    for r in records:
        decisions.update(r['decisions'])
        for line in (ROOT / r['trace_path']).read_text().splitlines():
            row = json.loads(line)
            if row['kind'] == 'decision':
                chosen = row['data']['chosen']
                actions[chosen.get('card_id', chosen['action']['action'])] += 1
    return {'actions': dict(actions), 'decisions': dict(decisions),
            'potions_remaining': [r.get('potions') for r in records],
            'forward_and_selection_ms_per_step': 1000 * sum(r['inference_seconds'] for r in records) /
                                               sum(r['steps'] for r in records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Preserve previous analysis')
    paths = {name: ROOT / 'artifacts/runs' / f'e125-{name}-v1.json'
             for name in ('fixtures', 'preflight', 'training', 'test')}
    reports = {k: json.loads(p.read_text()) for k, p in paths.items()}
    test, training = reports['test'], reports['training']
    combined_audit = audit(reports)
    assert combined_audit['pass']
    planner = test['planner']['records']; models = []
    for m, tr in zip(test['learners'], training['learners']):
        assert m['learner'] == tr['learner']
        assert all(r['verification_match'] for r in m['trained']['records'])
        for cp in tr['checkpoints']:
            assert file_hash(ROOT / cp['path']) == cp['sha256']
        selected = m['trained']['records']; initial = m['initial']['records']
        diffs = [x['hp'] - p['hp'] for x, p in zip(selected, planner)]
        models.append({'learner': m['learner'], 'selected_update': m['selected']['update'],
                       'test_rows': [{'case': p['case'], 'planner_hp': p['hp'], 'initial_status': i['status'],
                                      'initial_hp': i.get('hp'), 'selected_status': s['status'],
                                      'selected_hp': s['hp'], 'hp_delta_vs_planner': s['hp']-p['hp']}
                                     for p, i, s in zip(planner, initial, selected)],
                       'initial_summary': m['initial']['summary'], 'selected_summary': m['trained']['summary'],
                       'median_hp_delta_vs_planner': statistics.median(diffs),
                       'mean_hp_delta_vs_planner': statistics.mean(diffs),
                       'initial_behavior': behaviors(initial), 'selected_behavior': behaviors(selected),
                       'training_episodes': sum(len(u['episodes']) for u in tr['updates']),
                       'training_steps': sum(u['summary']['steps'] for u in tr['updates']),
                       'optimizer_seconds': sum(u['optimization_seconds'] for u in tr['updates']),
                       'training_wall_seconds_with_validation': tr['seconds'],
                       'parameters': tr['parameters'],
                       'validation_curve': [{k: v[k] for k in ('update', 'summary')} for v in tr['validations']]})
    result = {'sources': {k: {'path': str(p.relative_to(ROOT)), 'sha256': file_hash(p)} for k, p in paths.items()},
              'audit': combined_audit, 'planner_summary': test['planner']['summary'],
              'planner_behavior': behaviors(planner), 'models': models,
              'selected_policy_replays_pass': True, 'selected_policy_replays': 32,
              'all_model_checkpoint_hashes_pass': True, 'independent_test_seeds': 16,
              'training_episode_total': sum(m['training_episodes'] for m in models),
              'training_step_total': sum(m['training_steps'] for m in models),
              'continue_training_gate': test['continue_training_gate'],
              'scope_notes': [
                  'V1 preparation failed; v2 moved every original seed to first combat before training.',
                  'One 1702 initial-policy action cap is censored, never relabeled as defeat or scored zero.',
                  'Original aggregate test pass remains false; both selected policies and all 32 replays pass separately.',
                  'Both selected policies lose median 6 HP versus the planner, exceeding the preregistered 5-HP tolerance.',
                  'Model inference metric includes tensor preparation/forward/selection, excludes feature encoding and engine I/O.',
                  'Defend counts describe behavior on different resulting paths; no causal counterfactual benefit is inferred.',
                  'Two learners share the same 16 held-out game seeds, not 32 independent seeds.',
                  'No full-run, Elite, high-ascension, multi-character or general foresight claim.'
              ]}
    write(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('models', 'scope_notes', 'sources')}, indent=2))


if __name__ == '__main__':
    main()
