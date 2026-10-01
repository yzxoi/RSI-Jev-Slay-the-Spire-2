"""Audited room-entry checkpoint experiments; no coordinate/RNG/state editing."""
import hashlib
import json
from pathlib import Path
import time
import uuid

from .battle_search import baseline_choice, boundary, choices_for, finish, macro_choice
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


def battle_steps(frozen, record):
    """Recover a fully hashed E120 selected path; never substitute another plan."""
    path = ROOT / record['trace_path']
    if file_hash(path) != record['trace_sha256'] or file_hash(path.parent / 'wire.jsonl') != record['wire.jsonl_sha256']:
        raise ValueError('Selected E120 path evidence changed')
    pairs = wire_pairs(path.parent / 'wire.jsonl')
    count = len(frozen['prefix'])
    if [c for c, _ in pairs[:count]] != frozen['prefix']:
        raise ValueError('E120 selected plan prefix mismatch')
    before = pairs[count - 1][1]
    if digest(before) != frozen['entry_hash']:
        raise ValueError('E120 selected plan entry mismatch')
    steps = []
    for command, after in pairs[count:]:
        steps.append({'before': digest(before), 'action': command, 'after': digest(after)})
        before = after
    if digest([s['action'] for s in steps]) != record['path_hash'] or digest(before) != record['final_hash']:
        raise ValueError('E120 selected plan continuation mismatch')
    return steps


def continuation_path(frozen, version, label, mode, steps, expected_map,
                      checkpoint=None, extend=False):
    """A freezes a future path; B/C verify the identical complete action history."""
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**version, 'scope': 'E121_continuation', 'case': frozen['case'],
                   'label': label, 'mode': mode, 'extend': extend,
                   'checkpoint': checkpoint, 'input_path_hash': digest(steps)})
    started = time.monotonic()
    deadline = started + 30
    result = {'case': frozen['case'], 'label': label, 'mode': mode, 'run_id': uid,
              'status': 'error', 'steps_checked': 0, 'extension_steps': 0, 'steps': [],
              'restore_seconds': None, 'map_match': False, 'entry_match': False}
    engine = None
    previous = frozen['previous']
    try:
        engine = Headless(trace.directory, timeout=15, resource_decisions=True)
        def send(command):
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('Continuation deadline')
            engine.timeout = min(15, left)
            return engine.send(command)
        if mode.startswith('C'):
            path = ROOT / checkpoint['path']
            if file_hash(path) != checkpoint['sha256']:
                raise ValueError('Checkpoint hash changed')
            state = send({'cmd': 'load_save', 'path': str(path)})
        else:
            for command in frozen['prefix'][:-1]:
                state = send(command)
        require_map(state)
        result['map_match'] = digest(state) == digest(expected_map)
        if not result['map_match']:
            result['differences'] = differences(expected_map, state)
            raise ValueError('Map restore mismatch')
        if mode == 'B':
            file = trace.directory / 'map-checkpoint.json'
            save_started = time.monotonic()
            saved = send({'cmd': 'write_continue_save', 'path': str(file)})
            result['save_seconds'] = time.monotonic() - save_started
            if not saved.get('success') or saved.get('room_type') != 'MapRoom':
                raise ValueError('Save call was not a real map checkpoint')
            result['created_checkpoint'] = {'path': str(file.relative_to(ROOT)), 'sha256': file_hash(file)}
        enter = frozen['prefix'][-1]
        if enter not in [c['action'] for c in choices_for(state)]:
            raise ValueError('Original room entry is no longer legal')
        state = send(enter)
        result['restore_seconds'] = time.monotonic() - started
        result['entry_match'] = digest(state) == frozen['entry_hash']
        if not result['entry_match']:
            raise ValueError('Combat entry mismatch')

        def advance(chosen):
            nonlocal state, previous
            before = digest(state)
            trace.write('selected', {'before': before, 'choice': chosen})
            state = send(chosen['action'])
            result['steps'].append({'before': before, 'action': chosen['action'], 'after': digest(state)})
            previous = chosen

        for i, step in enumerate(steps):
            if digest(state) != step['before']:
                result['mismatch_step'] = i
                raise ValueError('Continuation before-state mismatch')
            chosen = next((c for c in choices_for(state) if c['action'] == step['action']), None)
            if chosen is None:
                raise ValueError('Frozen action is no longer legal')
            advance(chosen)
            if digest(state) != step['after']:
                result.update(mismatch_step=i, expected_after=step['after'], actual_after=digest(state))
                raise ValueError('Continuation after-state mismatch')
            result['steps_checked'] += 1
        if extend:
            result['battle_status'] = boundary(state)
            if result['battle_status'] is None:
                raise ValueError('E120 path did not end at a battle boundary')
            in_battle = False
            next_combat_round = None
            for _ in range(81):
                if state['decision'] == 'game_over':
                    result['stop_reason'] = 'game_over'
                    break
                if state['decision'] == 'combat_play':
                    in_battle = True
                    if next_combat_round is None:
                        next_combat_round = state['round']
                    if state['round'] > next_combat_round:
                        result['stop_reason'] = 'next_combat_second_turn'
                        break
                if result['extension_steps'] == 80:
                    raise TimeoutError('Post-battle extension action cap')
                if in_battle and boundary(state):
                    in_battle = False
                chosen = baseline_choice(state, previous) if in_battle else macro_choice(state)
                if chosen['action'] not in [c['action'] for c in choices_for(state)]:
                    raise ValueError('Extension policy nominated an illegal action')
                advance(chosen)
                result['extension_steps'] += 1
        result.update(status='match', final_hash=digest(state), final_decision=state['decision'],
                      final_context=state.get('context'), path_hash=digest(result['steps']))
        if checkpoint and file_hash(ROOT / checkpoint['path']) != checkpoint['sha256']:
            raise ValueError('Loading mutated the checkpoint file')
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    # Plan data is kept in the frozen bank as well as the raw transition wire.
    finish(trace, result, engine, started)
    return result
