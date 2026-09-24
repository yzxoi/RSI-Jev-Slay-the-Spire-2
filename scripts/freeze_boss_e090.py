"""Freeze four E089 Boss entries with exact command prefixes and source hashes."""

import argparse
import hashlib
import json
from pathlib import Path


CASES = [
    ('e089_holdout_004', 'Ironclad'),
    ('e089_holdout_005', 'Silent'),
    ('e089_holdout_006', 'Regent'),
    ('e089_holdout_006', 'Necrobinder'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boss_entry(path):
    selected = []
    for line in path.open(encoding='utf-8'):
        row = json.loads(line)
        kind, data = row['kind'], row['data']
        if kind == 'before':
            state = data['state']
            context = state.get('context') or {}
            if (state.get('decision') == 'combat_play' and context.get('act') == 1
                    and context.get('room_type') == 'Boss'):
                return len(selected), data['state_hash'], state, selected
        elif kind == 'selected':
            selected.append(data['action'])
    raise RuntimeError(f'No Act 1 Boss entry in {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.source_root / 'experiments/E089/result.json').read_text())
    runs = {(r['seed'], r['character'], r['policy']): r for r in result['results']}
    output = {'schema_version': 1, 'source_experiment': 'E089',
              'source_gameplay_sha': result['manifest']['code_commit'], 'cases': []}
    summaries = []
    for seed, character in CASES:
        run = runs[seed, character, 'retaliate']
        assert run['status'] == 'normal_defeat' and run['act'] == 1 and run['floor'] == 17
        trace_path = args.source_root / run['trace_path']
        wire_path = trace_path.with_name('wire.jsonl')
        assert sha(trace_path) == run['trace_sha256']
        index, entry_hash, state, selected = boss_entry(trace_path)
        commands = [json.loads(line)['data'] for line in wire_path.open(encoding='utf-8')
                    if json.loads(line)['kind'] == 'command']
        assert commands and commands[0]['cmd'] == 'start_run'
        prefix = commands[1:index + 1]
        assert len(prefix) == index and prefix == selected
        context = state['context']
        output['cases'].append({
            'id': f'{seed}_{character.lower()}', 'seed': seed, 'character': character,
            'ascension': 10, 'entry_decision_index': index,
            'entry_state_hash': entry_hash, 'act': 1, 'floor': context['floor'],
            'boss_id': context['boss']['id'], 'boss_name': context['boss']['name'],
            'source_trace_sha256': run['trace_sha256'], 'source_wire_sha256': sha(wire_path),
            'prefix_actions': prefix,
        })
        summaries.append({'id': output['cases'][-1]['id'], 'entry_hash': entry_hash,
                          'prefix_actions': len(prefix), 'hp': state['player']['hp'],
                          'max_hp': state['player']['max_hp'], 'boss': context['boss']['name']})
    target = Path('experiments/E090/fixtures.json')
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == '__main__':
    main()
