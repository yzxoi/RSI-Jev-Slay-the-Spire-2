"""Authorize one potion at the first materially threatening Act 1 state."""

from .potions import with_potions
from .numerical import intent_damage


def resource_check(state, planning):
    context = state.get('context') or {}
    if context.get('act') != 1 or state.get('decision') != 'combat_play':
        return None
    potions = with_potions(state, [])
    if not potions:
        return None
    player = state.get('player') or {}
    hp, maximum = player.get('hp'), player.get('max_hp')
    if not isinstance(hp, (int, float)) or not isinstance(maximum, (int, float)) or maximum <= 0:
        return None
    room = context.get('room_type')
    loss = planning.get('predicted_total_hp_loss') or 0
    incoming = sum(intent_damage(enemy) for enemy in state.get('enemies', []))
    if incoming <= 0 or room not in ('Elite', 'Boss', 'Monster'):
        return None
    if len(player.get('potions') or []) >= 2 and loss >= 8 and (
            room in ('Elite', 'Boss') or (room == 'Monster' and hp <= .5 * maximum)):
        reason = 'stocked_material_threat'
    elif hp <= .35 * maximum and loss >= 5:
        reason = 'low_hp_material_threat'
    else:
        return None
    brief = {
        'scope': 'The controller authorized spending exactly one potion in this materially threatening fight. Choose the best legal potion and target; after use, the engine state will be observed and cards replanned.',
        'reason': reason,
        'act': context.get('act'), 'floor': context.get('floor'), 'room_type': room,
        'known_boss': (context.get('boss') or {}).get('name'),
        'hp': hp, 'max_hp': maximum,
        'predicted_this_turn_hp_loss_without_potion': loss,
        'visible_incoming_damage_before_block': incoming,
        'guidance': 'Compare the legal potions and targets for immediate HP saved, faster enemy removal, and any lasting battle effect. Select the one with the largest expected contribution to winning this run. The budget has already made the spend-versus-reserve decision.',
    }
    return brief, potions
