"""One early, state-bound potion budget decision in risky Act 1 combats."""

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
    if room in ('Elite', 'Boss') and state.get('round') == 1:
        reason = 'elite_or_boss_opener'
    elif room == 'Monster' and hp <= .45 * maximum and loss >= 5 and incoming > 0:
        reason = 'low_hp_attacking_monster'
    else:
        return None
    reserve = {'id': 'reserve', 'action': {'action': 'reserve_potions'},
               'name': 'Reserve potions for a later fight'}
    brief = {
        'scope': 'Choose at most one potion at this encounter checkpoint; after use the engine state will be observed and cards replanned.',
        'reason': reason,
        'act': context.get('act'), 'floor': context.get('floor'), 'room_type': room,
        'known_boss': (context.get('boss') or {}).get('name'),
        'hp': hp, 'max_hp': maximum,
        'predicted_this_turn_hp_loss_without_potion': loss,
        'visible_incoming_damage_before_block': incoming,
        'guidance': 'Use a potion now when its actual effect meaningfully lowers defeat risk or saves substantial HP in this encounter. Do not wait for certain death; retain it when this fight is easy or the offered effect has little value. Compare every legal target. One potion use consumes a limited future resource.',
    }
    return brief, [reserve, *potions]
