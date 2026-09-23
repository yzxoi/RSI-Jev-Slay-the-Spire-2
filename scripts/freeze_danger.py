"""Freeze earliest recorded combat `before` per floor/turn in E051 and E054."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


SOURCES = {
    'F1GR9R0YXCCC': (
        '429c5ca1-d70c-4eba-ba69-25adc43fc383', '1e3fe3ef-43cc-48b2-b2be-aad01ce09480',
        '27abfff2-99f9-45c0-9f96-bd44d55c3238', '1685f06b-8f18-4be7-8c96-cc68da465af6',
        'de6f1b56-6f03-4a13-aa5f-e1ee42f0e25b', '7e480db4-bed5-4f51-ab36-28ea35cd7982',
        '9538849f-a1f0-47b1-b7c4-fb6e1ae5fdeb', '4ee77e11-f790-4367-a804-39e5e6265813',
        'f1cd5299-9293-4fbe-8d82-23b536fb1a69', '09cac380-a2c2-48fc-8def-a6936286304c',
        'bf7dd85e-0134-449b-ad71-e4bc400307e0', 'c0461bda-4ad3-4011-82c3-372d033e65b6',
    ),
    'DCEND0WRAPGL': (
        '5ceb2885-5e58-4e11-925d-b6a48269f097', '9a3eec25-1f67-4c65-96d0-32ba286c8228',
        '742313db-2a17-4898-bc5f-da8b2e6e1f5e', 'be84b32b-c9d6-4197-a692-2a9be2ace8f7',
        'd410c8ec-0887-4c6e-a470-6091628528d4', 'aff8d967-1c96-4d17-9c66-05e617cf8a8f',
    ),
}


def freeze(roots):
    cases, hashes = [], {}
    for run_id, segments in SOURCES.items():
        earliest = {}
        for segment in segments:
            path = roots[run_id] / segment / 'decisions.jsonl'
            hashes[segment] = hashlib.sha256(path.read_bytes()).hexdigest()
            for line in path.open():
                row = json.loads(line)
                if row.get('kind') != 'before':
                    continue
                state = (row.get('data') or {}).get('state') or {}
                if state.get('run_id') != run_id or state.get('screen') != 'COMBAT':
                    continue
                floor, turn = (state.get('run') or {}).get('floor'), state.get('turn')
                key = (floor, turn)
                if key in earliest and earliest[key][0] <= row['time']:
                    continue
                combat = state['combat']
                small = {'run_id': run_id, 'screen': 'COMBAT', 'turn': turn,
                         'run': {'floor': floor, 'current_hp': state['run']['current_hp'],
                                 'relics': state['run'].get('relics', [])},
                         'combat': {'action_readiness': combat.get('action_readiness'),
                                    'player': combat['player'], 'hand': combat['hand'],
                                    'enemies': combat['enemies'],
                                    'end_turn_will_kill_player': combat.get('end_turn_will_kill_player')}}
                earliest[key] = (row['time'], {'segment': segment, 'source_seq': row['seq'], 'state': small})
        expected = 78 if run_id == 'F1GR9R0YXCCC' else 53
        assert len(earliest) == expected, (run_id, len(earliest))
        cases.extend(value[1] for _, value in sorted(earliest.items()))
    counts = Counter(c['state']['run_id'] for c in cases)
    return {'schema_version': 1, 'kind': 'frozen_native_turn_starts_not_simulated_outcomes',
            'run_counts': dict(counts), 'source_hashes': hashes, 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--e051-runs', type=Path, required=True)
    parser.add_argument('--e054-runs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frozen = freeze({'F1GR9R0YXCCC': args.e051_runs, 'DCEND0WRAPGL': args.e054_runs})
    content = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(content, mtime=0))
    print(json.dumps({'cases': len(frozen['cases']), 'run_counts': frozen['run_counts'],
                      'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))
