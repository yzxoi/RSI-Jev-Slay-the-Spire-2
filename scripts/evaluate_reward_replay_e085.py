"""E085: exact-entry reward choice replays under one downstream policy."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.matched import MatchedJev
from rsi.progress import progress
from rsi.trace import version_manifest


FIXTURE_PATH = Path('experiments/E085/fixtures.json')
FIXTURE = json.loads(FIXTURE_PATH.read_text())
CONFIGS = [
    {'case_id': case['id'], 'arm': arm, 'character': case['character'],
     'seed': case['seed'], 'ascension': case['ascension'], 'policy': 'retaliate',
     'max_steps': 2000, 'max_seconds': 300,
     'replay_prefix_actions': case['prefix_actions'],
     'expected_entry_hash': case['entry_state_hash'],
     'forced_first_action': case[f'{arm}_choice']['action']}
    for case in FIXTURE['cases'] for arm in ('baseline', 'treatment')
]


def trace_audit(path):
    entry = []
    forced = []
    first_selected = None
    boss_floors = set()
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            kind, data = row['kind'], row['data']
            if kind == 'replay_entry':
                entry.append(data)
            elif kind == 'forced_reward':
                forced.append(data)
            elif kind == 'selected' and first_selected is None:
                first_selected = data['action']
            elif kind == 'before':
                context = (data['state'].get('context') or {})
                if context.get('act') == 1 and str(context.get('room_type')).lower() == 'boss':
                    boss_floors.add(context.get('floor'))
    return {'entry': entry, 'forced': forced, 'first_selected': first_selected,
            'act1_boss_entries': len(boss_floors)}


def label(left, right):
    return 'better' if right > left else 'worse' if right < left else 'tie'


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation and fixtures before evaluation')
    budget = Budget(max_calls=2000, max_usd=.50, conservative_failures=True)
    jev = MatchedJev(Jev(budget))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda config: episode(config, manifest, jev), CONFIGS))
    by_key = {(run['case_id'], run['arm']): run for run in results}
    for run in results:
        path = ROOT / run['trace_path']
        run['trace_verified'] = hashlib.sha256(path.read_bytes()).hexdigest() == run['trace_sha256']
        audit = trace_audit(path)
        run['entry_verified'] = (len(audit['entry']) == 1
                                 and audit['entry'][0]['state_hash'] == run['expected_entry_hash']
                                 and run.get('initial_state_hash') == run['expected_entry_hash'])
        run['forced_reward_verified'] = (len(audit['forced']) == 1
                                         and audit['forced'][0]['action'] == run['forced_first_action']
                                         and audit['first_selected'] == run['forced_first_action'])
        run['act1_boss_entries'] = audit['act1_boss_entries']
        run['prefix_action_count'] = len(run.pop('replay_prefix_actions'))
    pairs = []
    for case in FIXTURE['cases']:
        baseline = by_key[case['id'], 'baseline']
        treatment = by_key[case['id'], 'treatment']
        original = label(tuple(case['original_baseline_progress']),
                         tuple(case['original_treatment_progress']))
        replayed = label(progress(baseline), progress(treatment))
        pairs.append({'case_id': case['id'], 'character': case['character'], 'seed': case['seed'],
                      'original_direction': original, 'replay_direction': replayed,
                      'reproduces_original': original == replayed,
                      'reverses_original': original != replayed and replayed != 'tie',
                      'baseline_progress': [baseline.get('act'), baseline.get('floor')],
                      'treatment_progress': [treatment.get('act'), treatment.get('floor')],
                      'baseline_status': baseline['status'], 'treatment_status': treatment['status']})
    output = {'schema_version': 1, 'experiment': 'E085', 'manifest': manifest,
              'fixture_sha256': hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
              'configs': [{key: value for key, value in config.items()
                           if key != 'replay_prefix_actions'} for config in CONFIGS],
              'results': results, 'pairs': pairs,
              'trace_hashes_verified': sum(run['trace_verified'] for run in results),
              'budget': {'attempted_calls': budget.calls,
                         'provider_reported_cost_usd': sum(run['cost_usd'] for run in results),
                         'budgeted_spend_usd': budget.spent,
                         'uncertain_calls': budget.uncertain_calls,
                         'estimated_unknown_usd': budget.estimated_usd}}
    Path('experiments/E085/result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'statuses': dict(Counter(run['status'] for run in results)),
                      'entry_verified': sum(run['entry_verified'] for run in results),
                      'forced_reward_verified': sum(run['forced_reward_verified'] for run in results),
                      'trace_hashes_verified': output['trace_hashes_verified'],
                      'original_directions_reproduced': sum(pair['reproduces_original'] for pair in pairs),
                      'original_directions_reversed': sum(pair['reverses_original'] for pair in pairs),
                      'pair_directions': [(pair['case_id'], pair['original_direction'], pair['replay_direction'])
                                          for pair in pairs],
                      'budget': output['budget']}), flush=True)


if __name__ == '__main__':
    main()
