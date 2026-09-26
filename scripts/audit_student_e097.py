"""Recheck every raw E097 selection and battle trace against published results."""
import json

from rsi.engine import ROOT
from rsi.teacher import terminal
from rsi.trace import digest
from scripts.search_teacher_e096 import file_hash


def main():
    directory = ROOT / 'experiments/E097'
    data = json.loads((directory / 'result.json').read_text())
    checks = {key: 0 for key in ('selection_hash', 'request_count', 'policy_binding',
                                 'battle_hash', 'wire_hash', 'trajectory_hash',
                                 'legal_actions', 'real_boundary', 'no_debug_commands',
                                 'no_battle_model_calls')}
    requests = []
    for result in data['results']:
        path = ROOT / result['selection_trace_path']
        rows = [json.loads(line) for line in path.open()]
        calls = [r['data'] for r in rows if r['kind'] == 'model_request']
        requests.extend(calls)
        checks['selection_hash'] += file_hash(path) == result['selection_trace_sha256']
        checks['request_count'] += len(calls) == (0 if result['arm'] == 'lookup' else 1)
        selected = next(r['data'] for r in rows if r['kind'] == 'selected_profile')
        run = result['battle']
        checks['policy_binding'] += selected['policy'] == result['policy'] == run['policy']
        path = ROOT / run['trace_path']
        checks['battle_hash'] += file_hash(path) == run['trace_sha256']
        checks['wire_hash'] += file_hash(path.with_name('wire.jsonl')) == run['wire_sha256']
        rows = [json.loads(line) for line in path.open()]
        transitions = []
        legal = True
        choices = []
        before = command = None
        for row in rows:
            kind, value = row['kind'], row['data']
            if kind == 'before':
                before = value['state_hash']
                assert before == digest(value['state'])
            elif kind == 'candidates':
                choices = value
            elif kind == 'selected':
                legal &= value in choices
                command = value['action']
            elif kind == 'after':
                assert digest(value['state']) == value['state_hash']
                transitions.append([before, command, value['state_hash']])
                final_state = value['state']
        checks['trajectory_hash'] += digest(transitions) == run['trajectory_sha256']
        checks['legal_actions'] += legal
        checks['real_boundary'] += terminal(final_state) == result['status']
        checks['no_battle_model_calls'] += not any(r['kind'] == 'model_request' for r in rows)
        wires = [json.loads(line) for line in path.with_name('wire.jsonl').open()]
        checks['no_debug_commands'] += all(r['data']['cmd'] in ('start_run', 'action')
                                            for r in wires if r['kind'] == 'command')
    output = dict(runs=len(data['results']), checks_passed=checks,
                  total_model_requests=len(requests),
                  unique_request_hashes=len({digest(r) for r in requests}),
                  all_passed=all(n == len(data['results']) for n in checks.values()),
                  tested_sha=data['manifest']['code_commit'])
    (directory / 'audit.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
