"""Conservative native combat-exhaust selection guard."""


def _incoming(raw):
    return sum(
        max(0, int(intent.get('total_damage') or 0))
        for enemy in (raw.get('combat') or {}).get('enemies', [])
        if enemy.get('is_alive', True)
        for intent in enemy.get('intents', [])
        if intent.get('intent_type') == 'Attack'
    )


def preserve_exhaust_block(raw, offered):
    """Protect an affordable Evil Eye when exhausting it would waste urgent block.

    Native selections currently lack a typed source-card field, so we recognize
    explicit exhaust prompts and this observed conditional-block interaction only.
    """
    report = {'applied': False, 'reason': 'outside_supported_exhaust_selection'}
    selection = raw.get('selection') or {}
    if (raw.get('screen') != 'CARD_SELECTION' or not raw.get('in_combat')
            or selection.get('kind') != 'combat_hand_select'
            or not any(word in (selection.get('prompt') or '').lower() for word in ('消耗', 'exhaust'))):
        return offered, report
    player = (raw.get('combat') or {}).get('player') or {}
    hp = int(player.get('current_hp') or 0)
    block = int(player.get('block') or 0)
    energy = int(player.get('energy') or 0)
    incoming = _incoming(raw)
    report = {'applied': False, 'reason': 'insufficient_threat',
              'incoming': incoming, 'hp': hp, 'block': block, 'energy': energy}
    if hp <= 0 or incoming <= block or incoming < max(12, (hp + 1) // 2):
        return offered, report
    cards = {c.get('index'): c for c in selection.get('cards', [])}
    protected = {}
    for candidate in offered:
        action = candidate.get('action') or {}
        card = cards.get(action.get('option_index'))
        if action.get('action') != 'select_deck_card' or not card or card.get('card_id') != 'EVIL_EYE':
            continue
        cost = card.get('energy_cost')
        block_value = next((v.get('current_value') for v in card.get('dynamic_values', [])
                            if v.get('name') == 'Block'), 0)
        if not isinstance(cost, int) or not 0 <= cost <= energy or not isinstance(block_value, (int, float)):
            continue
        # Exhausting another card satisfies Evil Eye's same-turn bonus.
        if 2 * block_value >= 8:
            protected[action['option_index']] = 2 * block_value
    kept = [c for c in offered if (c.get('action') or {}).get('option_index') not in protected]
    if not protected or not kept:
        report['reason'] = 'no_affordable_conditional_block_or_alternative'
        return offered, report
    report.update(applied=True, reason='preserve_affordable_conditional_block',
                  protected_option_indices=list(protected), protected_block=protected)
    return kept, report
