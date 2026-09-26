"""Resource decision evidence shared by the CLI and native controllers."""
import copy

POTION_QUESTION = ('Use a potion now to prevent meaningful HP loss or enable a kill, '
                   'or execute the computed next card. Potions refill; do not hoard at risk of death.')


def require_resource_interface(state):
    if not isinstance(state.get('player', {}).get('potion_capacity'), int):
        raise RuntimeError('Resource interface missing: rebuild the pinned CLI with the E093 patch')


def potion_decision(state, strategy, planning, selected, potions):
    choices = [dict(c, id=f'p{i:03}') for i, c in enumerate([selected] + potions)]
    return {'state': state, 'strategy': strategy, 'question': POTION_QUESTION, 'plan': planning}, choices


def legacy_projection(state):
    """Remove only new observational fields; preserve all pre-existing game data."""
    state = copy.deepcopy(state)
    player = state.get('player', {})
    for key in ('potion_capacity', 'has_open_potion_slots', 'can_use_or_remove_potions'):
        player.pop(key, None)
    for potion in player.get('potions', []):
        for key in ('id', 'slot_index', 'usage', 'can_use', 'can_discard'):
            potion.pop(key, None)
    if state.get('decision') == 'shop':
        for potion in state.get('potions', []):
            potion.pop('id', None)
            potion.pop('can_buy', None)
    return state


def inventory(state):
    return [p.get('id', p['name']) for p in state.get('player', {}).get('potions', [])]
