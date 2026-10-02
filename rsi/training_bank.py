"""Natural battle pools and per-entry save certification, without game edits."""
import json
import time
import uuid

from .battle_search import baseline_choice, boundary, choices_for, compact, finish, macro_choice
from .checkpoints import continuation_path, file_hash, require_map, wire_pairs
from .engine import ROOT, Headless
from .ppo_env import episode
from .research_restore import ENGINE_KEYS
from .trace import Trace, digest


def collect(config, manifest):
    started = time.monotonic()
    deadline = started + 120
    trace = Trace(ROOT / 'artifacts/runs' / str(uuid.uuid4()),
                  {**manifest, 'scope': 'E133_preparation', 'config': config})
    result = {**config, 'status': 'error', 'entries': [], 'steps': 0}
    engine = None
    previous = None
    before_last = None
    active = False
    prefix = [dict(cmd='start_run', character=config['character'], seed=config['seed'],
                   ascension=config['ascension'])]
    try:
        engine = Headless(trace.directory, timeout=10, resource_decisions=True)
        state = engine.send(prefix[0])
        for step in range(1201):
            if state.get('decision') == 'game_over':
                result['status'] = 'natural_defeat'
                break
            if active and boundary(state):
                active = False
            if state.get('decision') == 'combat_play' and not active:
                active = True
                ordinal = len(result['entries']) + 1
                p, context = state['player'], state['context']
                native = bool(before_last and before_last.get('decision') == 'map_select'
                              and before_last.get('context', {}).get('room_type') == 'Map'
                              and prefix[-1].get('action') == 'select_map_node')
                entry = {**config, 'case': f"{config['case']}-b{ordinal}", 'ordinal': ordinal,
                         'seed_index': config['index'], 'status': 'ready', 'prefix': list(prefix),
                         'prefix_hash': digest(prefix), 'entry_hash': digest(state),
                         'previous': previous, 'floor': context['floor'], 'room_type': context['room_type'],
                         'hp': p['hp'], 'max_hp': p['max_hp'], 'deck_hash': digest(p['deck']),
                         'deck_size': p['deck_size'], 'entry_potions': p['potions'],
                         'entry_relics': p['relics'], 'enemies': [e['name'] for e in state['enemies']],
                         'native_map_available': native,
                         'restore_reason': 'true_map_boundary' if native else 'event_or_nonmap_entry',
                         'map_hash': digest(before_last) if native else None}
                result['entries'].append(entry)
                trace.write('entry', {'case': entry['case'], 'state': state})
                if context['room_type'] in ('Elite', 'Boss') or ordinal == 8:
                    result['status'] = 'ready'
                    break
            if step == 1200 or time.monotonic() >= deadline:
                result['status'] = 'preparation_cap'
                break
            chosen = baseline_choice(state, previous) if active else macro_choice(state)
            if chosen['action'] not in [c['action'] for c in choices_for(state)]:
                raise ValueError('Illegal preparation action')
            trace.write('selected', {'before': digest(state), 'choice': chosen})
            before_last = state
            engine.timeout = max(.01, min(10, deadline - time.monotonic()))
            state = engine.send(chosen['action'])
            prefix.append(chosen['action'])
            previous = chosen
            result['steps'] += 1
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finish(trace, result, engine, started)
    for f in result['entries']:
        f.update({k: result[k] for k in ('trace_path', 'trace_sha256', 'wire.jsonl_sha256',
                                       'engine.stderr.log_sha256')})
    return result


def entry_map(frozen):
    """An entry's prefix may be a strict prefix of a longer preparation trace."""
    path = ROOT / frozen['trace_path']
    wire = path.with_name('wire.jsonl')
    if file_hash(path) != frozen['trace_sha256'] or file_hash(wire) != frozen['wire.jsonl_sha256']:
        raise ValueError('Changed preparation evidence')
    pairs = wire_pairs(wire)
    n = len(frozen['prefix'])
    if n < 2 or [c for c, _ in pairs[:n]] != frozen['prefix']:
        raise ValueError('Entry does not match its preparation prefix')
    if digest(pairs[n-1][1]) != frozen['entry_hash']:
        raise ValueError('Preparation combat entry mismatch')
    state = pairs[n-2][1]
    require_map(state)
    if digest(state) != frozen['map_hash']:
        raise ValueError('Preparation map hash mismatch')
    return state


def matched(a, b):
    return all(a.get(k) == b.get(k) for k in ('status', 'final_hash', 'transition_hash', 'steps'))


def certify(f, manifest, deadline):
    result = {'case': f['case'], 'status': 'unstarted', 'native': f['native_map_available']}
    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError('Certification phase budget exhausted; no new path started')
    try:
        check()
        a, _ = episode(f, manifest, 'certificate:A')
        result['A'] = compact(a)
        if a['status'] not in ('clear', 'defeat'):
            raise ValueError('Full-prefix control did not reach a real terminal')
        if not result['native']:
            check()
            b, _ = episode(f, manifest, 'certificate:full_prefix_replay', expected=a['plan'])
            result['fallback_replay'] = compact(b)
            if not matched(a, b):
                raise ValueError('Full-prefix fallback replay mismatch')
        else:
            expected_map = entry_map(f)
            check()
            b = continuation_path(f, manifest, 'certificate', 'B', a['plan'], expected_map, extend=True)
            result['B'] = {k: v for k, v in b.items() if k != 'steps'}
            if b['status'] != 'match':
                raise ValueError('Save-call/continuation side-effect check failed')
            saved = b['created_checkpoint']
            native = json.loads((ROOT / saved['path']).read_text())
            if native['rng']['seed'] != f['seed'] or native['ascension'] != f['ascension']:
                raise ValueError('Saved original seed/ascension mismatch')
            snapshot = {**saved, **{k: f[k] for k in ('case', 'prefix_hash', 'entry_hash', 'map_hash')},
                        'engine': {k: manifest[k] for k in ENGINE_KEYS}, 'allow_unpromoted': True,
                        'performance_promotion_pass': False, 'validation_scope': 'E133 per-entry A/B/C1/C2'}
            check()
            c1 = continuation_path(f, manifest, 'certificate', 'C1', b['steps'], expected_map,
                                   checkpoint=snapshot)
            result['C1'] = {k: v for k, v in c1.items() if k != 'steps'}
            if c1['status'] != 'match' or c1.get('path_hash') != b['path_hash'] or c1.get('final_hash') != b['final_hash']:
                raise ValueError('Loaded reward/draw continuation mismatch')
            check()
            c2, _ = episode(f, manifest, 'certificate:C2_ppo_reset', expected=a['plan'], checkpoint=snapshot)
            result['C2'] = compact(c2)
            if not matched(a, c2) or file_hash(ROOT / saved['path']) != saved['sha256']:
                raise ValueError('PPO checkpoint reset replay/file mismatch')
            result['snapshot'] = snapshot
        result['status'] = 'match'
    except Exception as exc:
        result.update(status='fail', error=f'{type(exc).__name__}: {exc}')
    return result
