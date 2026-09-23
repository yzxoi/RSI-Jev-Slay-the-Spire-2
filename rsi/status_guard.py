"""Conservative native candidate filter for lethal retained Toxic cards."""

import re


def _amount(entity, power_id):
    return sum(p.get('amount', 0) for p in entity.get('powers', []) if p.get('power_id') == power_id)


def _damage(card):
    return next((v.get('current_value', v.get('base_value', 0)) for v in card.get('dynamic_values', []) if v.get('name') == 'Damage'), 0)


def _hp_loss(card):
    values = [v.get('current_value', v.get('base_value')) for v in card.get('dynamic_values', []) if v.get('name') == 'HpLoss']
    return values[0] if len(values) == 1 and isinstance(values[0], int) and values[0] > 0 else None


def _known_nonlethal_attack(card, target, enemies, allow_vulnerable=False):
    """Return True only when this one play cannot remove the visible attack."""
    if target is None:
        return False
    attackers = [e for e in enemies if any(i.get('total_damage') for i in e.get('intents', []))]
    # A single kill among multiple attackers may prevent enough damage to
    # survive. This narrow guard does not try to prove that counterfactual.
    if len(attackers) != 1:
        return False
    enemy = next((e for e in enemies if e['index'] == target), None)
    # Vulnerable changes target damage and can turn a nominally small attack
    # into lethal; abstain rather than excluding that candidate.
    harmless = {'STRENGTH_POWER', 'WEAK_POWER'}
    if allow_vulnerable:
        harmless.add('VULNERABLE_POWER')
    if enemy is None or any(p.get('power_id') not in harmless for p in enemy.get('powers', [])):
        return False
    ident = card.get('card_id')
    damage = _damage(card)
    if ident and ident.startswith('STRIKE_'):
        replay = re.search(r'(?:重放|Replay)\s*(\d+)', card.get('resolved_rules_text', ''), re.I)
        hits = 1 + (int(replay.group(1)) if replay else 0)
    elif ident == 'DISMANTLE':
        hits = 1
    else:
        return False
    if enemy['index'] != attackers[0]['index']:
        return True
    # 2x is a conservative upper bound for the standard 1.5x Vulnerable
    # modifier. Keep the Toxic baseline's older abstention by default.
    multiplier = 2 if allow_vulnerable and _amount(enemy, 'VULNERABLE_POWER') else 1
    return damage * hits * multiplier < enemy['current_hp'] + enemy.get('block', 0)


def reserve_toxic_energy(state, candidates):
    """Reserve energy only when clearing known Toxic cards can avert projected death.

    Status damage is treated as direct HP loss. This is a conservative forecast,
    not a claim about all native damage ordering or unknown triggers.
    """
    report = {'excluded': False, 'reason': 'no_actionable_toxic_risk'}
    if state.get('screen') != 'COMBAT' or state.get('selection'):
        return candidates, report
    combat = state['combat']; player = combat['player']; hand = combat['hand']
    toxic = [c for c in hand if c.get('card_id') == 'TOXIC' and c.get('playable')]
    if not toxic or any(c.get('energy_cost') != 1 for c in toxic):
        return candidates, report
    toxic_damage = _damage(toxic[0])
    if toxic_damage <= 0 or any(_damage(c) != toxic_damage for c in toxic):
        return candidates, report
    enemies = [e for e in combat['enemies'] if e.get('is_alive')]
    incoming = sum(i.get('total_damage') or 0 for e in enemies for i in e.get('intents', []))
    plating = _amount(player, 'PLATING_POWER')
    clasp = any(r.get('relic_id') == 'CLOAK_CLASP' for r in state['run'].get('relics', []))
    energy = player['energy']; hp = player['current_hp']; block = player['block']

    def loss(cleared):
        end_block = block + plating + (len(hand) - cleared if clasp else 0)
        return max(0, incoming - end_block) + toxic_damage * (len(toxic) - cleared)

    current_loss = loss(0)
    needed = next((n for n in range(1, len(toxic) + 1) if loss(n) < hp), None)
    if current_loss < hp or needed is None or needed > energy:
        return candidates, report
    byindex = {c['index']: c for c in hand}
    filtered = []; excluded = []
    for choice in candidates:
        action = choice['action']; kind = action['action']
        if kind == 'end_turn':
            excluded.append(choice['id']); continue
        if kind == 'play_card':
            card = byindex.get(action['card_index'])
            if card and card.get('card_id') != 'TOXIC' and card.get('energy_cost', 0) > energy - needed:
                if _known_nonlethal_attack(card, action.get('target_index'), enemies):
                    excluded.append(choice['id']); continue
        filtered.append(choice)
    if not filtered:
        return candidates, report
    report.update(excluded=bool(excluded), reason='reserve_energy_for_toxic',
                  toxic_count=len(toxic), clear_needed=needed, energy=energy,
                  incoming=incoming, current_projected_loss=current_loss,
                  cleared_projected_loss=loss(needed), excluded_ids=excluded)
    return filtered, report


def beckon_endturn_projection(state):
    """Project visible attack plus retained Beckon's direct HP loss only."""
    if state.get('screen') != 'COMBAT' or state.get('selection'):
        return None
    combat = state['combat']; player = combat['player']; hand = combat['hand']
    beckons = [c for c in hand if c.get('card_id') == 'BECKON']
    if not beckons:
        return None
    values = [_hp_loss(c) for c in beckons]
    if any(v is None for v in values):
        return {'known': False, 'reason': 'beckon_hp_loss_missing'}
    enemies = [e for e in combat['enemies'] if e.get('is_alive')]
    incoming = sum(i.get('total_damage') or 0 for e in enemies for i in e.get('intents', []))
    plating = _amount(player, 'PLATING_POWER')
    clasp = any(r.get('relic_id') == 'CLOAK_CLASP' for r in state['run'].get('relics', []))
    hp = player['current_hp']; block = player['block']

    def loss(cleared):
        remaining = [v for c, v in zip(beckons, values) if c['index'] not in cleared]
        end_block = block + plating + (len(hand) - len(cleared) if clasp else 0)
        return max(0, incoming - end_block) + sum(remaining)

    return {'known': True, 'hp': hp, 'energy': player['energy'], 'incoming': incoming,
            'block': block, 'beckon_count': len(beckons), 'beckon_indices': [c['index'] for c in beckons],
            'retained_hp_loss': sum(values), 'projected_loss': loss(set()), 'loss_after_clearing': loss}


def reserve_beckon_energy(state, candidates):
    """Keep a proven Beckon-clearing survival line before spending its energy."""
    projection = beckon_endturn_projection(state)
    report = {'excluded': False, 'reason': 'no_actionable_beckon_risk'}
    if not projection or not projection['known']:
        return candidates, report
    if projection['projected_loss'] < projection['hp']:
        return candidates, report
    hand = state['combat']['hand']; energy = projection['energy']
    beckons = [c for c in hand if c.get('card_id') == 'BECKON']
    if not all(c.get('playable') and c.get('energy_cost') == 1 for c in beckons):
        return candidates, report
    available = {c['action'].get('card_index') for c in candidates if c['action']['action'] == 'play_card'}
    if not all(c['index'] in available for c in beckons):
        return candidates, report
    # Hand sizes are small. Search actual card indices because modified copies
    # can have different HpLoss values and Cloak Clasp changes with hand size.
    from itertools import combinations
    indices = [c['index'] for c in beckons]
    survival_sets = [set(group) for n in range(1, min(energy, len(indices)) + 1)
                     for group in combinations(indices, n)
                     if projection['loss_after_clearing'](set(group)) < projection['hp']]
    if not survival_sets:
        return candidates, report
    needed = min(map(len, survival_sets))
    byindex = {c['index']: c for c in hand}
    enemies = [e for e in state['combat']['enemies'] if e.get('is_alive')]
    kept = []; excluded = []
    for choice in candidates:
        action = choice['action']; kind = action['action']
        if kind == 'end_turn':
            excluded.append(choice['id']); continue
        if kind == 'play_card':
            card = byindex.get(action['card_index'])
            if card and card.get('card_id') != 'BECKON' and card.get('energy_cost', 0) > energy - needed:
                if _known_nonlethal_attack(card, action.get('target_index'), enemies, allow_vulnerable=True):
                    excluded.append(choice['id']); continue
        kept.append(choice)
    if not kept:
        return candidates, report
    report.update(excluded=bool(excluded), reason='reserve_energy_for_beckon',
                  hp=projection['hp'], energy=energy, incoming=projection['incoming'],
                  retained_hp_loss=projection['retained_hp_loss'],
                  current_projected_loss=projection['projected_loss'], clear_needed=needed,
                  cleared_projected_loss=min(projection['loss_after_clearing'](s) for s in survival_sets),
                  excluded_ids=excluded)
    return kept, report
