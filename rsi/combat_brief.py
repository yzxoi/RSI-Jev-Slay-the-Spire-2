"""Small, auditable reward context derived from the preceding actual fight."""


def start_combat(state):
    context = state.get('context') or {}
    player = state.get('player') or {}
    return {
        'act': context.get('act'),
        'floor': context.get('floor'),
        'room_type': context.get('room_type'),
        'enemies': [enemy.get('name') for enemy in state.get('enemies', [])],
        'hp_in': player.get('hp'),
        'max_hp': player.get('max_hp'),
        'rounds': state.get('round') or 1,
    }


def update_combat(combat, state):
    combat['rounds'] = max(combat['rounds'], state.get('round') or 1)


def finish_combat(combat, state):
    hp_out = (state.get('player') or {}).get('hp')
    hp_in = combat['hp_in']
    return {**combat, 'hp_out': hp_out,
            'net_hp_loss': hp_in - hp_out if hp_in is not None and hp_out is not None else None}


def reward_brief(state, last_combat):
    """Return a brief only for a reward immediately following this floor's fight."""
    if state.get('decision') != 'card_reward' or not last_combat:
        return None
    context = state.get('context') or {}
    if (context.get('act'), context.get('floor')) != (last_combat['act'], last_combat['floor']):
        return None
    player = state.get('player') or {}
    boss = context.get('boss') or {}
    hp = player.get('hp')
    maximum = player.get('max_hp')
    loss = last_combat['net_hp_loss']
    if hp is None or maximum is None or loss is None:
        return None
    if hp <= maximum * .4:
        priority = 'Survival is critical: compare how each card changes the first two turns of the next fight, including immediate damage or block; reject slow cards you cannot safely deploy.'
    elif loss >= maximum * .2:
        priority = 'The last fight cost substantial HP: compare immediate damage, mitigation, energy cost and draw consistency before adding slow scaling.'
    elif (last_combat['rounds'] or 0) >= 6:
        priority = 'The last fight ran long: compare repeatable damage, scaling, draw and energy for a long fight; still check early-turn survival.'
    else:
        priority = 'The last fight was short with tolerable loss: compare each option against the next threat and the eventual Boss; avoid diluting the deck for a marginal card.'
    return {
        'act': context.get('act'), 'floor': context.get('floor'),
        'known_boss': boss.get('name'),
        'preceding_fight': last_combat,
        'current_hp': hp, 'max_hp': maximum,
        'decision_guidance': priority,
        'comparison': 'For every offered card, check cost/playability, first-two-turn effect, long-fight effect and existing deck synergy. Choose the largest improvement to run survival, or skip if none. The last fight is evidence, not a complete forecast.',
    }
