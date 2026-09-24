"""Conservative Act 1 potion reserve: boss-long buffs or imminent loss only."""

from .numerical import intent_damage
from .potions import with_potions


LONG_BOSS_BUFFS = ('Dexterity Potion', 'Strength Potion', 'Liquid Bronze', 'Fysh Oil')
RESCUE = ('Blood Potion', 'Block Potion', 'Weak Potion', 'Shackling Potion',
          'Swift Potion', 'Energy Potion')


def choose_horizon_potion(state, planning):
    """Return a legal potion candidate and reason, or (None, reason)."""
    context = state.get('context') or {}
    if context.get('act') != 1:
        return None, 'after_act_1'
    potions = state.get('player', {}).get('potions') or []
    if not potions:
        return None, 'no_potions'
    candidates = with_potions(state, [])
    if not candidates:
        return None, 'no_legal_potion_candidate'

    def select(potion, target=None):
        return next((candidate for candidate in candidates
                     if candidate['action']['args'].get('potion_index') == potion['index']
                     and candidate['action']['args'].get('target_index') == target), None)

    if context.get('room_type') == 'Boss' and state.get('round') == 1:
        for name in LONG_BOSS_BUFFS:
            for potion in potions:
                if potion.get('name') == name:
                    choice = select(potion)
                    if choice:
                        return choice, 'boss_long_buff'

    hp = state.get('player', {}).get('hp', 0)
    loss = planning.get('predicted_total_hp_loss', 0)
    if hp <= 0 or loss < hp:
        return None, 'reserve_for_future'

    for name in RESCUE:
        for potion in potions:
            if potion.get('name') != name:
                continue
            if potion.get('target_type') == 'AnyEnemy':
                enemies = state.get('enemies') or []
                enemy = max(enemies, key=intent_damage, default=None)
                choice = select(potion, enemy['index']) if enemy else None
            else:
                choice = select(potion)
            if choice:
                return choice, 'projected_lethal_rescue'

    # Direct damage is reserved unless it removes a currently attacking enemy.
    for potion in potions:
        if potion.get('name') not in ('Fire Potion', 'Explosive Ampoule'):
            continue
        damage = (potion.get('vars') or {}).get('Damage', 0)
        enemies = state.get('enemies') or []
        if potion.get('name') == 'Fire Potion':
            killable = [enemy for enemy in enemies
                        if enemy.get('hp', 0) + enemy.get('block', 0) <= damage
                        and intent_damage(enemy) > 0]
            if killable:
                target = max(killable, key=intent_damage)['index']
                choice = select(potion, target)
                if choice:
                    return choice, 'projected_lethal_kill'
        elif any(enemy.get('hp', 0) + enemy.get('block', 0) <= damage
                 and intent_damage(enemy) > 0 for enemy in enemies):
            choice = select(potion)
            if choice:
                return choice, 'projected_lethal_aoe'
    return None, 'no_known_rescue'
