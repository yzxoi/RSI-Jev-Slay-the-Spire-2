"""Small, versioned decision support distilled from audited native observations.

This is retrieved guidance, not a full simulator or a claim of causal benefit.
Both backends use the same builder; supplied current card rules take precedence.
"""
from collections import Counter
import re

VERSION = 'e033-v1'
SCALING = {'ROLLING_BOULDER', 'DEMON_FORM', 'FEEL_NO_PAIN', 'JUGGERNAUT',
           'CRIMSON_MANTLE', 'PYRE', 'CORRUPTION', 'BARRICADE', 'DARK_EMBRACE'}
LESSONS = [
    ({'FEEL_NO_PAIN', 'SECOND_WIND', 'JUGGERNAUT', 'DARK_EMBRACE'}, 'exhaust_engine',
     'When exhaust/block payoffs are present, install them before exhausting cards. Second Wind exhausts non-Attacks: count the actual remaining eligible cards, including unplayable curses/statuses. Its block and Feel No Pain block are separate gains per exhausted card. Exhaust can improve future draws. Do not exhaust needed draw/setup blindly.'),
    ({'JUGGERNAUT', 'IRON_WAVE', 'DAUGHTER_OF_THE_WIND', 'RAGE'}, 'block_triggers',
     'Active Juggernaut deals damage on each separate block gain, not just total block. Iron Wave own block and Daughter of the Wind attack-trigger block are separate triggers; Rage adds another. These triggers can make defense or a small attack the strongest lethal line. Against multiple enemies target allocation may be random; do not assume all hits land on one.'),
    ({'OFFERING', 'BATTLE_TRANCE', 'POMMEL_STRIKE', 'SHRUG_IT_OFF', 'SEEKER_STRIKE'}, 'draw_order',
     'Draw early enough to use the new cards and reveal setup/energy before committing remaining energy. Use free or energy-generating draw when its HP cost is affordable. Offering loses HP directly. Seeker selection should address this turn: a block/draw card, strong attack or still-affordable setup; it is not a permanent reward.'),
    ({'ROLLING_BOULDER', 'DEMON_FORM', 'PYRE', 'CRIMSON_MANTLE'}, 'delayed_setup',
     'One-turn search undervalues delayed powers. Establish scaling early in a long boss fight, preferably on a safe/buff turn, while retaining enough immediate defense. Rolling Boulder damage is power damage: enemy Vulnerable does not amplify it. Pyre supplies future energy, not instant energy. Crimson Mantle pays HP each turn; do not install at critically low HP without a survival plan.'),
    ({'DARK_SHACKLES', 'DISARM', 'INTIMIDATE'}, 'debuff_timing',
     'Temporary Strength reduction is especially valuable against multi-hit attacks. Use it on an attacking turn, not a buff turn. Check Artifact before counting debuffs. Strength reduction applies to each hit; round Vulnerable/Weak per hit using current rules.'),
    ({'FRANTIC_ESCAPE', 'SANDPIT'}, 'sandpit',
     'Sandpit expiry can kill regardless of HP/block and may be absent from lethal flags. Play Frantic Escape before spending its energy when countdown is low; do not end at countdown1 without preventing expiry.'),
    ({'CHAINS_OF_BINDING', 'QUEEN'}, 'queen_bound',
     'Queen binds the first cards drawn: only one Bound card may be played per turn. Prefer the Bound card that enables the best whole turn; extra draws can supply unbound cards. Do not plan a sequence containing multiple Bound cards.'),
    ({'CEREMONIAL_BEAST', 'PLOW'}, 'plow',
     'Ceremonial Beast Plow can be interrupted at its advertised HP threshold. Evaluate crossing that threshold as prevention of its attack, not only damage. Do not invent a threshold when the current state lacks it.'),
    ({'DISINTEGRATION', 'KNOWLEDGE_DEMON'}, 'disintegration',
     'Disintegration is blockable end-turn damage. Add its current amount to defense demand alongside enemy attacks. Do not equate it with direct HP loss or ignore it when enemy intent is non-attack.'),
    ({'GREED'}, 'eternal_curse',
     'Greed is Eternal and cannot be removed at a shop; do not make a future-removal plan for it. It can still be useful exhaust fodder in combat when a legal effect permits it.'),
]


def ident(obj):
    value = obj.get('card_id', obj.get('power_id', obj.get('relic_id', obj.get('enemy_id', obj.get('id', obj.get('name', ''))))))
    return re.sub(r'[^A-Z0-9]+', '_', str(value).split('.')[-1].upper()).strip('_').removesuffix('_POWER')


def stats(card):
    if 'dynamic_values' in card:
        return {v['name'].lower(): v.get('current_value', v.get('base_value', 0)) for v in card.get('dynamic_values') or []}
    return card.get('stats') or {}


def parts(state):
    if 'screen' in state:
        run = state.get('run') or {}; combat = state.get('combat') or {}
        player = combat.get('player') or run
        return run.get('deck', []), combat.get('hand', []), player.get('powers') or [], combat.get('enemies', []), run.get('relics', []), player
    player = state.get('player') or {}
    return player.get('deck', []), state.get('hand', []), state.get('player_powers') or [], state.get('enemies', []), player.get('relics') or [], player


def deck_profile(deck):
    counts = Counter(); costs = []
    for c in deck:
        st = stats(c); kind = c.get('type', c.get('card_type')); key = ident(c)
        counts[str(kind)] += 1
        counts['draw_cards'] += bool(st.get('cards', 0) or re.search(r'\bdraw\b|抽', c.get('description', c.get('resolved_rules_text', '')), re.I))
        counts['block_cards'] += bool(st.get('block', 0))
        counts['energy_cards'] += bool(st.get('energy', 0))
        counts['known_scaling_cards'] += key in SCALING
        cost = c.get('cost', c.get('energy_cost'))
        if isinstance(cost, (int, float)) and cost >= 0 and kind not in ['Curse', 'Status']: costs.append(cost)
    return {'size': len(deck), 'counts': dict(counts), 'mean_printed_cost': round(sum(costs) / len(costs), 2) if costs else None,
            'scope': 'Capability counts, not deck strength; only exported numeric/text features are counted.'}


def retrieval(state, choices=()):
    deck, hand, powers, enemies, relics, player = parts(state)
    objects = list(deck) + list(hand) + list(powers) + list(enemies) + list(relics)
    for e in enemies: objects.extend(e.get('powers') or [])
    for c in choices:
        detail = c.get('details')
        if isinstance(detail, dict): objects.append(detail)
    keys = {ident(o) for o in objects}
    # IDs may carry _BOSS/_POWER suffixes; native enemy IDs themselves are exact.
    keys |= {k.removesuffix('_BOSS') for k in keys}
    lessons = [{'id': name, 'guidance': text} for triggers, name, text in LESSONS if keys & triggers]
    return {'version': VERSION, 'deck_capabilities': deck_profile(deck), 'mechanic_lessons': lessons,
            'macro_priority': 'Solve current deck gaps instead of forcing the example winning deck. Early: efficient damage and enough block for immediate fights; then draw/energy and at least one reliable long-fight scaling plan. More cards are not automatically better. Prefer complementary cards; skip redundant weak rewards. Upgrades to draw/energy or central scaling often beat a starter damage upgrade. Buy for an explicit improvement; preserve survival resources. Rest if the next route is unsafe. Current supplied rules override these general lessons.',
            'planning_limit': 'The proposed turn is approximate and omits most draw/exhaust/block/relic chains and future turns. Re-evaluate it using current effects; do not treat its score as win probability.'}


def strategic_reasons(state):
    _, hand, powers, enemies, relics, _ = parts(state)
    legal = [c for c in hand if c.get('can_play', c.get('playable', False))]
    reasons = []
    if any(c.get('type', c.get('card_type')) == 'Power' for c in legal): reasons.append('playable_setup')
    if any(ident(c) in {'SECOND_WIND', 'OFFERING', 'SEEKER_STRIKE', 'HEADBUTT', 'BATTLE_TRANCE', 'FRANTIC_ESCAPE', 'DARK_SHACKLES'} for c in legal): reasons.append('draw_exhaust_or_special_choice')
    if any(ident(p) in {'JUGGERNAUT', 'FEEL_NO_PAIN', 'RAGE', 'DISINTEGRATION', 'CHAINS_OF_BINDING'} for p in powers): reasons.append('active_unmodeled_trigger')
    if any(ident(p) == 'SANDPIT' for e in enemies for p in e.get('powers') or []): reasons.append('boss_survival_countdown')
    return reasons
