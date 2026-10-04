"""E171 frozen, outcome-independent subset sampler; not a card-value model."""
import hashlib
import json

from .opening_subset import candidate_id, indexes
from .trace import digest


def bounded_choices(state, choices, baseline, domain):
    if domain['state_hash'] != digest(state):
        raise ValueError('Stale opening state')
    if len(choices) != domain['legal_subsets'] or not 1 <= len(choices) <= 32:
        raise ValueError('Incomplete or unsupported legal subset menu')
    by_id = {candidate_id(c): c for c in choices}
    if len(by_id) != len(choices):
        raise ValueError('Duplicate legal actions')
    if candidate_id(baseline) not in by_id:
        raise ValueError('Baseline outside legal menu')
    all_indices = sorted(c['index'] for c in state['cards'])
    negative = sorted(c['index'] for c in state['cards'] if c.get('type') in ('Status', 'Curse'))
    chosen = [by_id[candidate_id(baseline)]]
    for wanted in ([], all_indices, negative):
        c = next((c for c in choices if sorted(indexes(c)) == wanted), None)
        if c is None:
            raise ValueError('Missing required subset')
        if c not in chosen:
            chosen.append(c)

    def key(c):
        canonical = json.dumps(c['action'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256((domain['state_hash'] + canonical + 'e171').encode()).hexdigest()

    for c in sorted(choices, key=key):
        if len(chosen) >= min(8, len(choices)):
            break
        if c not in chosen:
            chosen.append(c)
    return chosen
