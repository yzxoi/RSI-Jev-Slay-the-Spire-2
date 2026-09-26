"""Experimental persistent room ownership and fresh semantic action binding."""
from .trace import digest


def route_entry(state):
    """Uncalibrated E099 hypothesis, not an estimated probability of failure."""
    deck = state.get('player', {}).get('deck', [])
    sustained = any((c.get('stats') or {}).get('poisonpower', 0) > 0 for c in deck)
    minions = any(any(p.get('name') == 'Minion' for p in e.get('powers') or [])
                  for e in state.get('enemies', []))
    return {'mode': 'astra' if minions and not sustained else 'plan',
            'features': {'minion_boss': minions, 'repeatable_poison': sustained},
            'reason': 'minion target allocation without repeatable poison' if minions and not sustained
                      else 'test bounded plan with repeated damage support'}


def bind_selector(selector, state, choices):
    """Resolve every action against current legal candidates; never reuse indices."""
    if set(selector) == {'choice'}:
        return next((c for c in choices if c['id'] == selector['choice']), None)
    matches = list(choices)
    if 'card' in selector:
        matches = [c for c in matches if c['action']['action'] == 'play_card' and c['name'] == selector['card']]
    elif 'potion' in selector:
        matches = [c for c in matches if c['action']['action'] == 'use_potion' and c['name'] == selector['potion']]
    elif selector.get('end_turn') is True:
        matches = [c for c in matches if c['action']['action'] == 'end_turn']
    else:
        return None
    if 'enemy' in selector:
        enemies = [e for e in state.get('enemies', []) if e['name'] == selector['enemy']]
        occurrence = selector.get('enemy_occurrence', 0)
        if not isinstance(occurrence, int) or occurrence < 0 or occurrence >= len(enemies):
            return None
        index = enemies[occurrence]['index']
        matches = [c for c in matches if c['action']['args'].get('target_index') == index]
    else:
        matches = [c for c in matches if 'target_index' not in c['action']['args']]
    if 'damage' in selector:
        hand = {c['index']: c for c in state.get('hand', [])}
        matches = [c for c in matches if (hand.get(c['action']['args'].get('card_index'), {}).get('stats') or {}).get('damage') == selector['damage']]
    # Identical-name copies may differ; default to current first copy, recorded in trace.
    return matches[0] if matches else None


class RoomOwner:
    def __init__(self, state, mode):
        self.entry_hash = digest(state)
        self.context = state.get('context')
        self.mode = mode
        self.queue = []
        self.round = None
        self.packet = None

    def accept(self, packet, state):
        if packet.get('state_hash') != digest(state):
            raise ValueError('Stale teacher packet')
        actions = packet.get('actions', [])
        if not 1 <= len(actions) <= 8 or not packet.get('reason'):
            raise ValueError('Expected reason and 1..8 semantic actions')
        if any('choice' in a for a in actions) and len(actions) != 1:
            raise ValueError('Candidate IDs are valid for exactly one fresh action')
        self.queue = list(actions)
        self.round = state.get('round')
        self.packet = packet

    def next(self, state, choices):
        if state.get('context') != self.context:
            self.queue = []
            raise ValueError('Room ownership expired')
        if self.queue and self.round != state.get('round'):
            self.queue = []
        if not self.queue:
            return None
        selector = self.queue.pop(0)
        chosen = bind_selector(selector, state, choices)
        if chosen is None:
            self.queue = []
        return chosen

    def observed(self, before, after):
        # A selection, a new turn, or newly drawn cards invalidates the remaining
        # current-hand sequence. Keep the room owner; request a new packet.
        old = {c['id'] for c in before.get('hand', [])}
        new = {c['id'] for c in after.get('hand', [])}
        if (after.get('decision') != 'combat_play' or after.get('round') != before.get('round')
                or not new.issubset(old) or after.get('draw_pile_count', 0) < before.get('draw_pile_count', 0)):
            self.queue = []
