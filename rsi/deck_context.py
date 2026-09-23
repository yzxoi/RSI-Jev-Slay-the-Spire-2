"""Compact arithmetic for Jev's reward and shop decisions."""


def deck_profile(state):
    deck = (state.get('player') or {}).get('deck') or []
    types = {'Attack': 0, 'Skill': 0, 'Power': 0}
    block = draw = energy = strikes = defends = 0
    for card in deck:
        kind = card.get('type')
        if kind in types:
            types[kind] += 1
        stats = card.get('stats') or {}
        block += int(isinstance(stats.get('block'), (int, float)) and stats['block'] > 0)
        draw += int(isinstance(stats.get('cards'), (int, float)) and stats['cards'] > 0)
        energy += int(isinstance(stats.get('energy'), (int, float)) and stats['energy'] > 0)
        ident = card.get('id') or ''
        strikes += int(ident.startswith('CARD.STRIKE_'))
        defends += int(ident.startswith('CARD.DEFEND_'))
    return {'deck_size': len(deck), 'attacks': types['Attack'], 'skills': types['Skill'],
            'powers': types['Power'], 'printed_block_cards': block,
            'printed_draw_cards': draw, 'printed_energy_cards': energy,
            'starter_strikes': strikes, 'starter_defends': defends,
            'attack_heavy': len(deck) >= 15 and types['Attack'] >= 2 * max(1, block)}


def deck_advice(profile):
    if profile['attack_heavy']:
        return ('Attack-heavy by printed-card counts. Consider reliable block or draw '
                'over a marginal extra attack when the offered card is good; still judge synergy, cost and upcoming boss.')
    return ('Use these counts as coverage signals, not card-quality scores. '
            'Judge the actual offered card, deck synergy and upcoming boss.')
