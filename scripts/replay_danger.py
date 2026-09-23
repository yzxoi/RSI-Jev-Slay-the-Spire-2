"""Fixed-state audit of old HP threshold versus E056 review signal."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from rsi.danger import review_projected_loss


def replay(fixture, danger_hp=20):
    rows = []; baseline = 0; added = 0; abstentions = {}
    for case in fixture['cases']:
        state = case['state']; player = state['combat']['player']; hp = player['current_hp']
        old = hp <= danger_hp and player['energy'] > 0
        report = review_projected_loss(state, danger_hp)
        baseline += int(old)
        added += int(report['review'] and not old)
        if report['reason'] not in ('projected_large_hp_loss', 'below_review_threshold', 'baseline_current_hp'):
            abstentions[report['reason']] = abstentions.get(report['reason'], 0) + 1
        if old or report['review']:
            rows.append({'run_id': state['run_id'], 'floor': state['run']['floor'],
                         'turn': state['turn'], 'hp': hp, 'baseline': old, **report})
    return {'schema_version': 1, 'kind': 'retrospective_review_signal_not_counterfactual_survival',
            'input_counts': fixture['run_counts'], 'states': len(fixture['cases']),
            'baseline_reviews': baseline, 'added_reviews': added,
            'abstentions': abstentions, 'reviews': rows,
            'source_hashes': fixture['source_hashes']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, default=Path('experiments/E056/frozen-turn-starts.json.gz'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    content = args.fixture.read_bytes()
    result = replay(json.loads(gzip.decompress(content)))
    result['fixture_sha256'] = hashlib.sha256(content).hexdigest()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'states': result['states'], 'baseline_reviews': result['baseline_reviews'],
                      'added_reviews': result['added_reviews'], 'abstentions': result['abstentions']}))
