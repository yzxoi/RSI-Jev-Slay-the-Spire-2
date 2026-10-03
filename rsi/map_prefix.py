"""Native Map saves with a verified short suffix to an arbitrary natural root."""
import json
from .checkpoints import file_hash, require_map, wire_pairs
from .engine import ROOT
from .research_restore import ENGINE_KEYS
from .trace import digest


def map_offset(root):
    source=ROOT/root['source_trace_path']
    if file_hash(source)!=root['source_trace_sha256']:
        raise ValueError('Changed source trace')
    pairs=wire_pairs(source.with_name('wire.jsonl'))[:len(root['prefix'])]
    if [c for c,_ in pairs]!=root['prefix'] or [digest(s) for _,s in pairs]!=root['prefix_state_hashes']:
        raise ValueError('Source Map evidence differs from frozen prefix')
    offsets=[i for i,(_,s) in enumerate(pairs) if s.get('decision')=='map_select' and s.get('context',{}).get('room_type')=='Map']
    if not offsets:raise ValueError('No genuine Map boundary before root')
    return offsets[-1]


def identity(root, snapshot, manifest):
    if any(snapshot[k]!=root[k] for k in ('case','prefix_hash','root_hash')):
        raise ValueError('Snapshot belongs to another root')
    if any(snapshot['engine'][k]!=manifest[k] for k in ENGINE_KEYS):
        raise ValueError('Snapshot runtime changed')
    path=ROOT/snapshot['path']
    if file_hash(path)!=snapshot['sha256']:raise ValueError('Native save bytes changed')
    save=json.loads(path.read_text())
    if save['ascension']!=root['ascension'] or save['rng']['seed']!=root['seed']:
        raise ValueError('Native save seed/ascension mismatch')
    offset=snapshot['map_offset']
    if not 0<=offset<len(root['prefix']) or snapshot['map_hash']!=root['prefix_state_hashes'][offset]:
        raise ValueError('Snapshot Map provenance mismatch')


def restore(send, root, manifest, directory, *, snapshot=None, capture=None):
    if (snapshot is None)==(capture is None):raise ValueError('Choose exactly one save/load mode')
    count=0
    if snapshot is not None:
        identity(root,snapshot,manifest)
        offset=snapshot['map_offset']
        state=send(dict(cmd='load_save',path=str(ROOT/snapshot['path'])));count+=1
        require_map(state)
        if digest(state)!=snapshot['map_hash']:raise ValueError('Loaded Map differs')
        start=offset+1
    else:
        offset=capture['map_offset'];start=0
    for i in range(start,len(root['prefix'])):
        state=send(root['prefix'][i]);count+=1
        if digest(state)!=root['prefix_state_hashes'][i]:raise ValueError('Restoration prefix differs')
        if capture is not None and i==offset:
            require_map(state)
            path=directory/'native-map.json'
            response=send(dict(cmd='write_continue_save',path=str(path)));count+=1
            if not response.get('success') or response.get('room_type')!='MapRoom':
                raise ValueError('Native save did not capture a Map')
            capture.update({k:root[k] for k in ('case','prefix_hash','root_hash')},
                map_hash=digest(state),path=str(path.relative_to(ROOT)),sha256=file_hash(path),
                engine={k:manifest[k] for k in ENGINE_KEYS})
            identity(root,capture,manifest)
    return state,count


def certified_snapshots(reference, bank_path, manifest):
    """Only the complete, immutable E158 exact-runtime certificate is consumable."""
    path=ROOT/reference['path']
    if file_hash(path)!=reference['sha256']:raise ValueError('Edited restoration certificate')
    report=json.loads(path.read_text())
    if not report.get('passed') or not report.get('fidelity_pass') or not report['audit']['pass']:
        raise ValueError('Restoration certificate did not pass')
    if any(report['manifest'][k]!=manifest[k] for k in ENGINE_KEYS):raise ValueError('Certificate runtime differs')
    if file_hash(bank_path)!=report['source_bank']['sha256']:raise ValueError('Certificate root bank differs')
    bank=json.loads(bank_path.read_text())
    if (len(report.get('fresh',[]))!=30 or len(report.get('loaded',[]))!=30 or
            any(r['status']!='complete' or len(r['checks'])!=n or not all(x['exact'] for x in r['checks'])
                for key,n in [('fresh',2),('loaded',4)] for r in report[key])):
        raise ValueError('Incomplete runtime-bridge proof')
    source_path=ROOT/report['source']['path']
    if file_hash(source_path)!=report['source']['sha256']:raise ValueError('Changed source references')
    source=json.loads(source_path.read_text())
    if any(source['manifest'][k]!=bank['manifest'][k] for k in ENGINE_KEYS):raise ValueError('Wrong source runtime')
    snapshots={s['case']:s for s in report['snapshots']}
    if len(snapshots)!=30 or set(snapshots)!={r['case'] for r in bank['roots']}:
        raise ValueError('Incomplete certified root coverage')
    for meta in bank['roots']:
        root_path=ROOT/meta['raw']['path']
        if file_hash(root_path)!=meta['raw']['sha256']:raise ValueError('Root artifact changed')
        identity(json.loads(root_path.read_text()),snapshots[meta['case']],manifest)
    return snapshots
