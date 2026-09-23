"""Execute one precommitted, state-bound native MCP action outside campaign screens."""
import argparse
import fcntl
import json
from pathlib import Path
import time
import uuid

from .engine import ROOT
from .mcp import MCP
from .scenes import fingerprint
from .trace import Trace, version_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--choice', required=True)
    parser.add_argument('--expected-run-id')
    parser.add_argument('--output', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit action and implementation before native execution')
    choice = json.loads(Path(args.choice).read_text())
    if set(choice) != {'state_hash', 'action', 'reason'} or not isinstance(choice['action'], dict):
        raise ValueError('Choice must contain exact state_hash, action, and reason')
    with Path('/tmp/rsi-sts2-native-8080.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        uid = str(uuid.uuid4())
        trace = Trace(ROOT / 'artifacts/runs' / uid,
                      {**manifest, 'scope': 'native_single_action', 'config': vars(args)})
        started = time.monotonic()
        result = {'run_id': uid, 'status': 'error', 'actions': 0}
        raw = {}
        try:
            mcp = MCP('http://127.0.0.1:8080/mcp', trace)
            health = mcp.call('health_check')
            if health.get('status') != 'ready' or health.get('play_running'):
                raise RuntimeError('Native game is not ready for a single writer')
            raw = mcp.call('get_raw_game_state')
            result.update(before_run_id=raw.get('run_id'), before_screen=raw.get('screen'),
                          before_state_hash=fingerprint(raw))
            if args.expected_run_id and raw.get('run_id') != args.expected_run_id:
                raise RuntimeError('Unexpected run ID before action')
            if result['before_state_hash'] != choice['state_hash']:
                raise RuntimeError('Precommitted state fingerprint is stale')
            action = choice['action']
            if action.get('action') not in raw.get('available_actions', []):
                raise RuntimeError('Precommitted action is not advertised as legal')
            trace.write('before', {'state': raw, 'state_hash': result['before_state_hash']})
            trace.write('expert_decision', choice)
            if not args.execute:
                result['status'] = 'read_only_ready'
            else:
                fresh = mcp.call('get_raw_game_state')
                if fingerprint(fresh) != choice['state_hash']:
                    raise RuntimeError('State changed before action delivery')
                if mcp.call('health_check').get('play_running'):
                    raise RuntimeError('Competing native autoplay became active')
                answer = mcp.call('act', {**action, 'raw_state': True,
                                          'reason': '程序摘要：预提交的单步原生操作；' + choice['reason']})
                result['actions'] = 1
                trace.write('action_result', answer)
                mcp.call('wait_until_actionable', {'timeout_seconds': 10, 'raw_state': True})
                raw = mcp.call('get_raw_game_state')
                trace.write('after', {'state': raw, 'state_hash': fingerprint(raw)})
                result['status'] = 'accepted'
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            trace.write('failure', {'error': result['error']})
        result.update(after_run_id=raw.get('run_id'), after_screen=raw.get('screen'),
                      after_state_hash=fingerprint(raw) if raw else None,
                      seconds=round(time.monotonic() - started, 3))
        trace.write('summary', result)
        result['trace_path'] = str(trace.path.relative_to(ROOT))
        result['trace_sha256'] = trace.close()
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({'manifest': manifest, 'result': result}, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'trace_path'}, ensure_ascii=False), flush=True)
        if result['status'] == 'error':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
