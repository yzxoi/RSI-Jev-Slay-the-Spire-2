"""Audited room-entry checkpoint experiments; no coordinate/RNG/state editing."""
import hashlib
import json
from pathlib import Path
import time
import uuid

from .battle_search import choices_for, finish
from .engine import ROOT, Headless
from .trace import Trace, digest


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def differences(expected, actual, path='', limit=16):
    out = []
    def visit(a, b, p):
        if len(out) >= limit or a == b:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(a.keys() | b.keys()):
                if k not in a or k not in b:
                    out.append({'path': p + '/' + k, 'expected': a.get(k), 'actual': b.get(k),
                                'missing': 'expected' if k not in a else 'actual'})
                else:
                    visit(a[k], b[k], p + '/' + k)
                if len(out) >= limit:
                    break
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                visit(x, y, p + '/' + str(i))
        else:
            out.append({'path': p, 'expected': a, 'actual': b})
    visit(expected, actual, path)
    return out


def wire_pairs(path):
    """Strict command/response pairs, excluding the initial ready message."""
    pending = None
    pairs = []
    for line in Path(path).read_text().splitlines():
        record = json.loads(line)
        if record['kind'] == 'command':
            if pending is not None:
                raise ValueError('Unanswered command in source wire')
            pending = record['data']
        elif record['kind'] == 'state' and pending is not None:
            pairs.append((pending, record['data']))
            pending = None
    if pending is not None:
        raise ValueError('Incomplete source wire')
    return pairs


def source_map(frozen):
    path = ROOT / frozen['trace_path']
    if file_hash(path) != frozen['trace_sha256']:
        raise ValueError('Fixture trace hash mismatch')
    wire = path.parent / 'wire.jsonl'
    if file_hash(wire) != frozen['wire.jsonl_sha256']:
        raise ValueError('Fixture wire hash mismatch')
    pairs = wire_pairs(wire)
    if [c for c, _ in pairs] != frozen['prefix']:
        raise ValueError('Fixture prefix mismatch')
    if frozen['prefix'][-1]['action'] != 'select_map_node':
        raise ValueError('Expected a map entry action')
    state = pairs[-2][1]
    require_map(state)
    return state


def require_map(state):
    if state.get('decision') != 'map_select' or state.get('context', {}).get('room_type') != 'Map':
        raise ValueError('Exact checkpoint requires a real map boundary')


def preflight_path(frozen, version, mode, expected_map, checkpoint=None):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**version, 'scope': 'E121_preflight', 'case': frozen['case'], 'mode': mode})
    started = time.monotonic()
    deadline = started + 20
    result = {'case': frozen['case'], 'mode': mode, 'run_id': uid, 'status': 'error',
              'map_match': False, 'entry_match': False, 'restore_seconds': None}
    engine = None
    try:
        engine = Headless(trace.directory, timeout=15, resource_decisions=True)
        def send(command):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Preflight deadline')
            engine.timeout = min(15, remaining)
            return engine.send(command)
        if mode == 'C':
            path = ROOT / checkpoint['path']
            if file_hash(path) != checkpoint['sha256']:
                raise ValueError('Checkpoint file changed')
            state = send({'cmd': 'load_save', 'path': str(path)})
        else:
            for command in frozen['prefix'][:-1]:
                state = send(command)
        result['map_hash'] = digest(state)
        result['map_match'] = digest(expected_map) == digest(state)
        if not result['map_match']:
            result['map_differences'] = differences(expected_map, state)
        require_map(state)
        if mode == 'B':
            file = trace.directory / 'map-checkpoint.json'
            before = time.monotonic()
            response = send({'cmd': 'write_continue_save', 'path': str(file)})
            result['save_seconds'] = time.monotonic() - before
            if not response.get('success') or response.get('room_type') != 'MapRoom':
                raise ValueError('Engine did not save a real map checkpoint')
            result['checkpoint'] = {'path': str(file.relative_to(ROOT)), 'sha256': file_hash(file)}
        command = frozen['prefix'][-1]
        if command not in [c['action'] for c in choices_for(state)]:
            raise ValueError('Room entry is not legal after restore')
        state = send(command)
        result['restore_seconds'] = time.monotonic() - started
        result['entry_hash'] = digest(state)
        result['entry_match'] = result['entry_hash'] == frozen['entry_hash']
        if not result['entry_match']:
            expected_entry = wire_pairs(ROOT / frozen['trace_path'].replace('decisions.jsonl', 'wire.jsonl'))[-1][1]
            result['entry_differences'] = differences(expected_entry, state)
        result['status'] = 'match' if result['map_match'] and result['entry_match'] else 'mismatch'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finish(trace, result, engine, started)
    return result


def preflight_case(frozen, version):
    expected = source_map(frozen)
    paths = []
    checkpoint = None
    for mode in ('A', 'B', 'C'):
        if mode == 'C' and checkpoint is None:
            paths.append({'mode': mode, 'status': 'unstarted', 'reason': 'No valid map snapshot'})
            continue
        result = preflight_path(frozen, version, mode, expected, checkpoint)
        paths.append(result)
        if mode == 'B':
            checkpoint = result.get('checkpoint')
    return {'case': frozen['case'], 'paths': paths,
            'status': 'match' if all(p['status'] == 'match' for p in paths) else 'fail'}
