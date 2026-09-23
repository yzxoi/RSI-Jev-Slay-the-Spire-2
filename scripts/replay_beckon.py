"""Compare E055 guard with the frozen baseline; never execute game actions."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from rsi.campaign import ordinary_candidates
from rsi.guard import filter_end_turn
from rsi.status_guard import beckon_endturn_projection, reserve_toxic_energy


def baseline(state, offered):
    choices, _ = filter_end_turn(state, offered)
    return reserve_toxic_energy(state, choices)[0]


def replay(fixture):
    changes = []
    lethal = []
    for index, case in enumerate(fixture['cases']):
        state, offered = case['state'], case['candidates']
        old = baseline(state, offered)
        new, report = ordinary_candidates(state, offered, 'room_guided')
        old_ids = {c['id'] for c in old}
        new_ids = {c['id'] for c in new}
        if new_ids != old_ids:
            changes.append({'case': index, 'turn': state['turn'],
                            'hp': state['combat']['player']['current_hp'],
                            'energy': state['combat']['player']['energy'],
                            'removed_ids': sorted(old_ids - new_ids),
                            'added_ids': sorted(new_ids - old_ids),
                            'reason': report['reason']})
        projection = beckon_endturn_projection(state)
        if projection and projection['known'] and projection['projected_loss'] >= projection['hp']:
            lethal.append({'case': index, 'turn': state['turn'], 'energy': projection['energy'],
                           'hp': projection['hp'], 'visible_loss': projection['projected_loss'],
                           'native_will_kill': state['combat'].get('end_turn_will_kill_player')})
    return {'schema_version': 1, 'kind': 'retrospective_candidate_replay_not_battle_simulation',
            'run_id': fixture['run_id'], 'source_hashes': fixture['source_hashes'],
            'states': len(fixture['cases']), 'changed_candidate_sets': len(changes),
            'changes': changes, 'projected_lethal_states': lethal}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, default=Path('experiments/E055/frozen-soul-fysh.json.gz'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture_bytes = args.fixture.read_bytes()
    result = replay(json.loads(gzip.decompress(fixture_bytes)))
    result['fixture_sha256'] = hashlib.sha256(fixture_bytes).hexdigest()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'states': result['states'], 'changed_candidate_sets': result['changed_candidate_sets'],
                      'projected_lethal_states': len(result['projected_lethal_states'])}))
