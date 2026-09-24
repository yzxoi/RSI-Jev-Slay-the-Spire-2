"""Opt-in Act 1 Boss opener for known battle-long potion buffs."""

from .potions import with_potions


PRIORITY = ('Liquid Bronze', 'Dexterity Potion', 'Strength Potion', 'Fysh Oil')


def choose_boss_buff(state, card_choices):
    """Return (legal potion candidate, expanded candidates), or (None, original)."""
    context = state.get('context') or {}
    if (context.get('act') != 1 or context.get('room_type') != 'Boss'
            or state.get('round') != 1):
        return None, card_choices
    if not state.get('player', {}).get('potions'):
        return None, card_choices
    expanded = with_potions(state, card_choices)
    for name in PRIORITY:
        choice = next((c for c in expanded
                       if c['action']['action'] == 'use_potion' and c['name'] == name), None)
        if choice:
            return choice, expanded
    return None, card_choices
