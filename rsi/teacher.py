"""Experimental, explicit proposal policies; only the engine certifies outcomes.

Not an exact simulator. These scores deliberately do not claim win probabilities.
The E096 search tests whole policies and keeps every failed branch.
"""
from .full import macro_candidates
from .numerical import intent_damage
from .planner import choose_plan
from .policy import combat_candidates
from .potions import with_potions
from .retaliation import hit_count


MODES = ('balanced', 'focus_leader', 'scaling', 'draw')
POTIONS = ('early', 'turn3', 'turn5', 'selective')


def power_amount(entity, name):
    return sum(p.get('amount', 0) for p in entity.get('powers') or []
               if name.casefold() in p.get('name', '').casefold())


def is_minion(enemy):
    return power_amount(enemy, 'Minion') > 0


def card_value(state, card, target, policy):
    """Marginal single-action estimate, evaluated again after every real action."""
    stats = card.get('stats') or {}
    mode = policy.get('round_modes', {}).get(str(state.get('round')), policy['mode'])
    enemies = state.get('enemies', [])
    relevant = [e for e in enemies if target is None or e['index'] == target]
    incoming = sum(intent_damage(e) for e in enemies)
    block_gap = max(0, incoming - state['player'].get('block', 0)
                    - state['player'].get('end_turn_block', 0))
    loss_price = policy['loss_price']
    block = min(block_gap, stats.get('block', 0))
    damage = kills = doom_value = 0.0
    previews = {p['target_index']: p for p in card.get('damage_by_target') or []}
    for enemy in relevant:
        leader_weight = 1.8 if mode == 'focus_leader' and not is_minion(enemy) else 1.0
        preview = previews.get(enemy['index'], {})
        # Preview damage may already include block, as in the baseline controller;
        # do not call this a certified transition or sum it into win evidence.
        hits = hit_count(card, preview)
        if 'twice' in card.get('description', '').lower():
            hits = max(2, hits)
        dealt = min(enemy['hp'], (preview.get('damage', 0) or 0) * hits)
        damage += dealt * leader_weight
        doom = stats.get('doompower', 0)
        ident = card.get('id', '').split('.')[-1]
        if ident == 'NO_ESCAPE':
            doom = stats.get('calculationbase', 0) + (
                power_amount(enemy, 'Doom') // max(1, stats.get('doomthreshold', 10))
            ) * stats.get('calculationextra', 0)
        doom_value += min(max(0, enemy['hp'] - power_amount(enemy, 'Doom')), doom) * leader_weight
        if dealt + doom + power_amount(enemy, 'Doom') >= enemy['hp']:
            kills += 8 + intent_damage(enemy) * loss_price
    description = card.get('description', '').lower()
    draw_now = stats.get('cards', 0) if 'draw {' in description else 0
    draw_weight = 7 if mode == 'draw' else 3
    utility = draw_now * draw_weight
    if card.get('type') == 'Power':
        utility += 22 if mode == 'scaling' else 10
    utility += stats.get('strengthpower', 0) * 7 + stats.get('dexteritypower', 0) * 8
    utility += stats.get('energy', 0) * 8
    utility += min(block_gap, stats.get('summon', 0)) * loss_price
    utility += stats.get('summon', 0) * (2 if mode == 'scaling' else .5)
    utility += stats.get('stars', 0) * (4 if state.get('stars', 0) < 3 else 1)
    utility += stats.get('shivs', 0) * 4
    utility += stats.get('vulnerablepower', 0) * 3
    utility += min(8, incoming * .25) if stats.get('weakpower') else 0
    hits_incoming = sum(i.get('hits', 1) for e in enemies
                        for i in e.get('intents', []) if i.get('damage', 0) > 0)
    utility += stats.get('damageback', 0) * hits_incoming * .85
    if card.get('id', '').endswith('.REFLECT'):
        utility += block * .85
    if card.get('id', '').endswith('.ARMAMENTS'):
        utility += 8
    score = damage * .85 + block * loss_price + kills + doom_value * (
        1.2 if mode == 'scaling' else .8) + utility
    # Opportunity cost: rank by energy efficiency; energy-zero does not divide by zero.
    cost = max(.65, card.get('cost', 0))
    return score / cost


def selection_choice(state, choices, policy, previous):
    cards = {c['index']: c for c in state.get('cards', [])}
    context = ' '.join(str(state.get(k, '')) for k in
                       ('prompt', 'selection_type', 'description', 'message')).lower()
    prior_name = (previous or {}).get('name', '').lower()
    harmful = any(word in context for word in ('discard', 'exhaust', 'remove', 'put on top'))
    harmful |= prior_name in ('survivor', 'photon cut', 'true grit', 'burning pact')
    def value(choice):
        args = choice['action']['args']
        indexes = ([args['card_index']] if 'card_index' in args else
                   [int(x) for x in args.get('indices', '').split(',') if x])
        total = 0
        for idx in indexes:
            c = cards.get(idx, {})
            stats = c.get('stats') or {}
            total += (stats.get('damage', 0) + stats.get('block', 0)
                      + stats.get('cards', 0) * 4 + stats.get('doompower', 0)
                      + (20 if c.get('type') == 'Power' else 0)
                      - (40 if c.get('type') in ('Status', 'Curse') else 0))
            if c.get('id', '').endswith('.NO_ESCAPE'):
                total += 25
        return (-total if harmful else total)
    ordered = sorted(choices, key=value, reverse=True)
    return ordered[min(policy.get('selection_rank', 0), len(ordered) - 1)]


def select(state, policy, previous=None):
    """Fresh candidates; policy has no stored hand/target indices or future states."""
    if state['decision'] != 'combat_play':
        choices = macro_candidates(state, {'previous': previous})
        chosen = selection_choice(state, choices, policy, previous)
        return chosen, choices, {'selection_rule': 'estimated_card_value'}
    choices = combat_candidates(state)
    if policy['mode'] == 'legacy':
        chosen, planning = choose_plan(state, choices, triggers=True, retaliation=True)
    else:
        cards = {c['index']: c for c in state['hand']}
        values = {}
        for c in choices:
            args = c['action']['args']
            values[c['id']] = (card_value(state, cards[args['card_index']],
                                         args.get('target_index'), policy)
                               if c['action']['action'] == 'play_card' else 0)
        chosen = max(choices, key=lambda c: values[c['id']])
        planning = {'scope': 'heuristic proposal, not engine prediction', 'scores': values}
    schedule = policy['potions']
    if schedule == 'none':
        return chosen, choices, planning
    potions = with_potions(state, [])
    round_min = {'early': 1, 'turn3': 3, 'turn5': 5, 'selective': 1}[schedule]
    if state['round'] < round_min:
        return chosen, choices, planning
    # Persistent buffs before transient resources. Duplicator follows the best
    # currently affordable card; re-evaluate after its real engine transition.
    best_card = next((c for c in state.get('hand', []) if
                     c['index'] == chosen['action']['args'].get('card_index')), {})
    for potion in sorted(potions, key=lambda c: (
            0 if c['name'] in ('Strength Potion', 'Dexterity Potion', 'Liquid Bronze', 'Power Potion')
            else 2 if c['name'] == 'Duplicator' else 1,
            c['action']['args'].get('target_index', -1))):
        name = potion['name']
        if name == 'Energy Potion' and (state.get('energy', 0) > 1 or
                                       not any(not c.get('can_play') and c.get('cost', 0) > 0
                                               and c.get('type') not in ('Status', 'Curse')
                                               for c in state.get('hand', []))):
            continue
        if name == 'Duplicator' and chosen['action']['action'] != 'play_card':
            continue
        if schedule == 'selective':
            if name == 'Duplicator' and (best_card.get('id', '').split('.')[-1] not in
                    ('ASTRAL_PULSE', 'NO_ESCAPE', 'FLAME_BARRIER', 'PERFECTED_STRIKE', 'REFLECT')
                    and best_card.get('type') != 'Power'):
                continue
            if name == 'Vulnerable Potion' and best_card.get('type') != 'Attack':
                continue
        target = potion['action']['args'].get('target_index')
        if target is not None and policy['mode'] == 'focus_leader':
            enemy = next(e for e in state['enemies'] if e['index'] == target)
            if is_minion(enemy):
                continue
        return potion, choices + potions, planning
    return chosen, choices + potions, planning


def terminal(state):
    """Do not mistake a potion-generated card reward for a combat victory."""
    if state.get('decision') == 'game_over':
        return 'boss_defeat'
    if state.get('decision') == 'combat_play':
        return None
    if state.get('decision') in ('card_select',):
        return None
    if state.get('decision') == 'card_reward':
        if state.get('from_event'):
            return None
        if 'gold_earned' not in state:
            raise RuntimeError('Unrecognized reward boundary')
        return 'boss_clear' if state.get('player', {}).get('hp', 0) > 0 else 'boss_defeat'
    if state.get('decision') in ('map_select', 'potion_reward'):
        return 'boss_clear' if state.get('player', {}).get('hp', 0) > 0 else 'boss_defeat'
    raise RuntimeError(f"Unexpected Boss decision boundary: {state.get('decision')}")
