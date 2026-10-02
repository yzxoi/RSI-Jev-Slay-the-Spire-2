"""Proof-bound full-prefix recovery, never a silent runtime save fallback."""
from .checkpoints import file_hash, wire_pairs
from .engine import ROOT
from .trace import digest

PROTOCOL = 'E134-conservative-full-prefix-v1'


def source_plan(frozen, record, *, continuation=False):
    path = ROOT/record['trace_path']
    if file_hash(path)!=record['trace_sha256'] or file_hash(path.with_name('wire.jsonl'))!=record['wire.jsonl_sha256']:
        raise ValueError('Original reference evidence changed')
    pairs = wire_pairs(path.with_name('wire.jsonl'))
    saves = [c for c,_ in pairs if c.get('cmd')=='write_continue_save']
    if len(saves)!=int(continuation):
        raise ValueError('Unexpected save-call count in original reference')
    pairs = [(c,s) for c,s in pairs if c.get('cmd')!='write_continue_save']
    count = len(frozen['prefix'])
    if [c for c,_ in pairs[:count]]!=frozen['prefix']:
        raise ValueError('Reference canonical prefix mismatch')
    state = pairs[count-1][1]
    if digest(state)!=frozen['entry_hash']:
        raise ValueError('Reference combat entry mismatch')
    steps = []
    for command, after in pairs[count:]:
        if command.get('cmd')!='action':
            raise ValueError('Non-action inside reference battle/continuation')
        steps.append(dict(before=digest(state),action=command,after=digest(after)))
        state = after
    expected = record['path_hash'] if continuation else record['transition_hash']
    if digest(steps)!=expected or digest(state)!=record['final_hash']:
        raise ValueError('Reference path/final hash mismatch')
    return steps


def recovery_valid(record):
    old = record.get('original_native_failure',{})
    paths = record.get('replays',[])
    if (record.get('status')!='match' or record.get('native') is not False
            or record.get('restore_reason')!='verified_full_prefix_recovery' or record.get('snapshot')
            or old.get('status')!='fail' or not old.get('native')
            or old.get('A',{}).get('status') not in ('clear','defeat')
            or old.get('B',{}).get('status')!='match'
            or old.get('C1',{}).get('status')=='match' or len(paths)!=3):
        return False
    for r in paths[:2]:
        if (r.get('status')!='match' or r.get('path_hash')!=old['B']['path_hash']
                or r.get('final_hash')!=old['B']['final_hash'] or r.get('mode')!='A'):
            return False
    p = paths[2]
    return p.get('restore_mode')=='full_prefix' and all(p.get(k)==old['A'].get(k)
        for k in ('status','steps','transition_hash','final_hash'))
