"""Read existing decision traces with source hash and state/choice checks."""
import json

from .engine import ROOT
from .checkpoints import file_hash, wire_pairs
from .trace import digest


def decisions(record, initial_previous=None):
    path = ROOT / record['trace_path']
    wire = path.with_name('wire.jsonl')
    if file_hash(path) != record['trace_sha256'] or file_hash(wire) != record['wire.jsonl_sha256']:
        raise ValueError('Changed source decision/wire evidence')
    states = {digest(s): s for _, s in wire_pairs(wire)}
    previous = initial_previous
    result = []
    for line in path.read_text().splitlines():
        item = json.loads(line)
        if item['kind'] != 'decision':
            continue
        d = item['data']
        state = states[d['before']]
        choices = d['candidates']
        selected = next(i for i, c in enumerate(choices) if c['action'] == d['chosen']['action'])
        if 'index' in d and selected != d['index']:
            raise ValueError('Trace action index mismatch')
        result.append(dict(state=state, choices=choices, previous=previous, index=selected,
                           value=d.get('value'), logprob=d.get('old_logprob')))
        previous = d['chosen']
    return result
