"""Fail-closed, opt-in use of fidelity-checked but unpromoted map snapshots."""
import json
from pathlib import Path

from .checkpoints import file_hash, require_map
from .engine import ROOT
from .trace import digest

ENGINE_KEYS = ('headless_assembly_sha256', 'headless_game_sha256', 'game_dll_sha256', 'godot_stubs_sha256')


def research_snapshots(index_path, manifest, *, allow_unpromoted=False):
    index = json.loads(Path(index_path).read_text())
    if not index.get('fidelity_pass'):
        raise ValueError('Checkpoint fidelity has not passed')
    if not index.get('performance_promotion_pass') and not allow_unpromoted:
        raise ValueError('Explicit research opt-in required for unpromoted checkpoints')
    evidence = {}
    for name, record in index['evidence'].items():
        path = ROOT / record['path']
        if file_hash(path) != record['sha256']:
            raise ValueError('Checkpoint evidence hash mismatch')
        evidence[name] = json.loads(path.read_text())
    fidelity = evidence['verification-v1.json']
    timing = evidence['timing-v2.json']
    if (not fidelity['correctness_pass'] or not fidelity['audit']['pass'] or
            len(fidelity['comparisons']) != 120 or
            any(not r['full_path_match'] or not r['final_match'] or r['status'] != 'match'
                for r in fidelity['comparisons'])):
        raise ValueError('Incomplete fidelity evidence')
    if timing['promotion_pass'] != index['performance_promotion_pass']:
        raise ValueError('Performance promotion was relabeled')
    for key in ENGINE_KEYS:
        if index['engine'].get(key) != manifest[key] or fidelity['manifest'].get(key) != manifest[key]:
            raise ValueError('Checkpoint engine version mismatch')
    snapshots = {}
    for entry in index['entries']:
        if entry['case'] in snapshots or file_hash(ROOT / entry['path']) != entry['sha256']:
            raise ValueError('Duplicate case or edited checkpoint')
        snapshots[entry['case']] = {**entry, 'engine': index['engine'],
                                   'allow_unpromoted': allow_unpromoted,
                                   'performance_promotion_pass': index['performance_promotion_pass'],
                                   'validation_index_sha256': file_hash(index_path)}
    return snapshots


def restore_entry(send, frozen, snapshot, manifest):
    if not snapshot.get('performance_promotion_pass') and not snapshot.get('allow_unpromoted'):
        raise ValueError('Unpromoted checkpoint restoration requires research opt-in')
    if snapshot['case'] != frozen['case'] or snapshot['prefix_hash'] != digest(frozen['prefix']):
        raise ValueError('Checkpoint belongs to another action history')
    if snapshot['entry_hash'] != frozen['entry_hash']:
        raise ValueError('Checkpoint entry identity mismatch')
    if any(snapshot['engine'].get(k) != manifest[k] for k in ENGINE_KEYS):
        raise ValueError('Checkpoint engine changed')
    path = ROOT / snapshot['path']
    if file_hash(path) != snapshot['sha256']:
        raise ValueError('Checkpoint bytes changed')
    state = send({'cmd': 'load_save', 'path': str(path)})
    require_map(state)
    if digest(state) != snapshot['map_hash']:
        raise ValueError('Restored map observation mismatch')
    from .battle_search import choices_for
    enter = frozen['prefix'][-1]
    if enter not in [c['action'] for c in choices_for(state)]:
        raise ValueError('Checkpoint room entry is not freshly legal')
    state = send(enter)
    if digest(state) != frozen['entry_hash']:
        raise ValueError('Restored battle entry mismatch')
    return state
