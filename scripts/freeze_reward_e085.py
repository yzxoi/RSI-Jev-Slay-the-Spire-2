"""Freeze selected E084 first-divergence prefixes without publishing game states."""

import argparse
import hashlib
import json
from pathlib import Path


CASES = [
    ('e084_jobs_001', 'Ironclad', 'e9e7175a4a2bbe1cdc7409d978a7f8bad10485a6c4648505ba03369bfd29139b'),
    ('e084_jobs_004', 'Regent', 'b2d60d7519875e322e0f1dea26fc959d960ffa749e6be52a4ad3b4cb03744cd5'),
    ('e084_jobs_001', 'Defect', 'f10361f34c9cc27cde49b977b2842f85b5a6cbde8b52a4f5a4afb8032de0c37c'),
    ('e084_jobs_003', 'Ironclad', 'c87bbdc9438228fd4050f84a3eab765bc536de334b6bad658777736813e503c7'),
    ('e084_jobs_001', 'Regent', '262a3bc35f35bb7e517561fd757f70b3a54aeb1be826b6bd41db0c63bf295a1e'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_events(path):
    state_hash = None
    candidates = None
    selected = []
    for line in path.open(encoding='utf-8'):
        row = json.loads(line)
        kind, data = row['kind'], row['data']
        if kind == 'before':
            state_hash = data['state_hash']
        elif kind == 'candidates':
            candidates = data
        elif kind == 'selected':
            selected.append({'state_hash': state_hash, 'action': data['action'],
                             'name': data.get('name'), 'candidates': candidates})
    return selected


def source_commands(path):
    commands = [json.loads(line)['data'] for line in path.open(encoding='utf-8')
                if json.loads(line)['kind'] == 'command']
    assert commands and commands[0]['cmd'] == 'start_run'
    return commands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.source_root / 'experiments/E084/result.json').read_text())
    runs = {(r['seed'], r['character'], r['policy']): r for r in result['results']}
    audits = {(a['seed'], a['character']): a for a in result['pair_audit']}
    output = {'schema_version': 1, 'source_experiment': 'E084',
              'source_gameplay_sha': result['manifest']['code_commit'], 'cases': []}
    for seed, character, expected_hash in CASES:
        baseline = runs[seed, character, 'retaliate']
        treatment = runs[seed, character, 'retaliate_deck_jobs']
        audit = audits[seed, character]
        index = audit['first_difference_index']
        assert audit['first_difference_valid_reward'] and audit['first_difference_state_hash'] == expected_hash
        trace_path = args.source_root / baseline['trace_path']
        wire_path = trace_path.with_name('wire.jsonl')
        assert sha(trace_path) == baseline['trace_sha256']
        selected = selected_events(trace_path)
        commands = source_commands(wire_path)
        prefix = commands[1:index + 1]
        assert len(prefix) == index
        assert prefix == [event['action'] for event in selected[:index]]
        assert selected[index]['state_hash'] == expected_hash
        legal = selected[index]['candidates']
        def chosen(action):
            choice = next(candidate for candidate in legal if candidate['action'] == action)
            return {'action': action, 'card_id': (choice.get('details') or {}).get('id'),
                    'name': (choice.get('details') or {}).get('name')}
        output['cases'].append({
            'id': f'{seed}_{character.lower()}', 'seed': seed, 'character': character,
            'ascension': 10, 'decision_index': index, 'entry_state_hash': expected_hash,
            'source_trace_sha256': baseline['trace_sha256'], 'source_wire_sha256': sha(wire_path),
            'prefix_actions': prefix,
            'baseline_choice': chosen(audit['baseline_action']),
            'treatment_choice': chosen(audit['treatment_action']),
            'original_baseline_progress': [baseline.get('act'), baseline.get('floor')],
            'original_treatment_progress': [treatment.get('act'), treatment.get('floor')],
        })
    path = Path('experiments/E085/fixtures.json')
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases': len(output['cases']),
                      'prefix_actions': [len(case['prefix_actions']) for case in output['cases']]}))


if __name__ == '__main__':
    main()
