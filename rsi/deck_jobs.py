"""Small, descriptive deck context for an opt-in card-reward experiment."""

REWARD_STRATEGY_SUFFIX = """ At this card reward, compare every offered card with Skip for the current run. Identify the nearest known Boss and relevant immediate threats without inventing an unseen encounter. Check whether the deck can do immediate single-target damage, handle multiple enemies, survive heavy turns, scale for a long fight, and draw/pay for its answers in time. Favor a card that fills an urgent missing job at a useful horizon; penalize setup that cannot be played safely, excess resource demand and dilution of existing answers. Potions and relics may already cover a job. Treat the supplied deck counts only as observations, not thresholds; use exact current card rules. Do not force an archetype or a fixed deck size."""


def reward_summary(state):
    """Count only fields directly available in the current headless state."""
    player = state.get('player') or {}
    deck = player.get('deck') or []

    def positive_stat(card, name):
        value = (card.get('stats') or {}).get(name, 0)
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0

    def nonstarter_attack(card):
        card_id = str(card.get('id') or '').split('.')[-1].upper()
        return card.get('type') == 'Attack' and not card_id.startswith('STRIKE_')

    return {
        'deck_size': len(deck),
        'nonstarter_attack_cards': sum(nonstarter_attack(card) for card in deck),
        'cards_with_direct_block_stat': sum(positive_stat(card, 'block') for card in deck),
        'upgraded_cards': sum(bool(card.get('upgraded')) for card in deck),
        'cards_costing_2_or_more_energy': sum(
            isinstance(card.get('cost'), (int, float))
            and not isinstance(card.get('cost'), bool)
            and card['cost'] >= 2 for card in deck
        ),
        'hp': player.get('hp'),
        'max_hp': player.get('max_hp'),
        'known_boss_id': ((state.get('context') or {}).get('boss') or {}).get('id'),
    }
