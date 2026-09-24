"""Replay frozen E074 headless commands without model or game-value edits."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from rsi.engine import Headless, ROOT
from rsi.trace import digest, version_manifest


def replay(case, expect_error):
    directory = ROOT / 'artifacts/runs' / f'e074-{uuid.uuid4()}'
    engine = Headless(directory)
    state = None
    result = {'name': case['name'], 'command_count': len(case['commands']),
              'source_wire_sha256': case['source_wire_sha256'],
              'expected_before_final_state_hash': case['before_final_state_hash']}
    try:
        for index, command in enumerate(case['commands']):
            if index == len(case['commands']) - 1:
                result['before_final_state_hash'] = digest(state)
                result['before_final_state_match'] = result['before_final_state_hash'] == case['before_final_state_hash']
                if not result['before_final_state_match']:
                    result['status'] = 'pre_state_mismatch'
                    break
            try:
                state = engine.send(command)
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
                result['failed_command_index'] = index
                result['status'] = ('expected_error' if expect_error and index == len(case['commands']) - 1
                                    and case['expected_error_substring'] in str(exc) else 'unexpected_error')
                break
        else:
            result['status'] = 'unexpected_success' if expect_error else 'accepted'
            result['final_decision'] = state.get('decision')
            result['final_state_hash'] = digest(state)
    finally:
        engine.close()
        result['wire_path'] = str((directory / 'wire.jsonl').relative_to(ROOT))
        result['wire_sha256'] = hashlib.sha256((directory / 'wire.jsonl').read_bytes()).hexdigest()
        result['engine_log_sha256'] = hashlib.sha256((directory / 'engine.stderr.log').read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-error', action='store_true')
    args = parser.parse_args()
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before replay')
    cases = json.loads((ROOT / 'experiments/E074/frozen-commands.json').read_text())['cases']
    results = [replay(case, args.expect_error) for case in cases]
    data = {'schema_version': 1, 'experiment': 'E074', 'phase': 'baseline' if args.expect_error else 'patched',
            'manifest': manifest, 'results': results}
    output = ROOT / 'experiments/E074' / ('baseline-result.json' if args.expect_error else 'patched-result.json')
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'phase': data['phase'], 'results': results}, ensure_ascii=False), flush=True)
    required = 'expected_error' if args.expect_error else 'accepted'
    if any(result['status'] != required for result in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
