"""Opt-in campaign subset protocol; never expands or changes PPO's action space."""
import math
from .engine import action
from .trace import digest


def contract(state):
    if state.get('decision') != 'card_select':
        raise ValueError('Expected card selection')
    cards = state['cards']
    indexes = [c['index'] for c in cards]
    lo, hi = state.get('min_select', 1), state.get('max_select', 1)
    if (any(type(i) is not int or i < 0 for i in indexes) or len(set(indexes)) != len(indexes)
            or type(lo) is not int or type(hi) is not int or not 0 <= lo <= min(hi, len(cards))):
        raise ValueError('Invalid selection domain')
    return dict(protocol='subset-v1', state_hash=digest(state), indexes=indexes,
                min_select=lo, max_select=min(hi, len(cards)),
                legal_subsets=sum(math.comb(len(cards), k) for k in range(lo, min(hi, len(cards))+1)))


def resolve(domain, indexes, state_hash):
    if domain['protocol'] != 'subset-v1' or domain['state_hash'] != state_hash:
        raise ValueError('Stale selection domain')
    if (not isinstance(indexes, list) or any(type(i) is not int for i in indexes)
            or len(set(indexes)) != len(indexes)
            or not domain['min_select'] <= len(indexes) <= domain['max_select']
            or not set(indexes) <= set(domain['indexes'])):
        raise ValueError('Illegal selection subset')
    # Match the engine menu order, including non-contiguous card indexes.
    chosen = [i for i in domain['indexes'] if i in set(indexes)]
    command = action('select_cards', indices=','.join(map(str, chosen))) if chosen else action('skip_select')
    return dict(id='subset', name=command['action'], action=command, details=dict(indexes=chosen))


def validate_fresh(state, selected):
    domain = contract(state)
    expected = resolve(domain, selected['details']['indexes'], digest(state))
    if selected != expected:
        raise ValueError('Changed subset action')
