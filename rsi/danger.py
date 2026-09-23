"""Read-only review signal for large visible native turn-start HP loss."""

from .status_guard import beckon_endturn_projection


def _value(card, name):
    values = [v.get('current_value', v.get('base_value')) for v in card.get('dynamic_values', [])
              if v.get('name') == name]
    return values[0] if len(values) == 1 and isinstance(values[0], int) else None


def review_projected_loss(state, danger_hp=20, min_loss=14):
    """Signal a review; never propose, remove or execute an action.

    The calculation is an alert about a plausible end-turn outcome, not a
    battle simulation. Abstain when an immediately playable card might remove
    an attacker or when attack totals are not structured.
    """
    report = {'review': False, 'reason': 'outside_turn_start', 'danger_hp': danger_hp,
              'min_loss': min_loss, 'scope': 'visible_attack_plus_known_beckon_only'}
    if state.get('screen') != 'COMBAT' or state.get('selection'):
        return report
    combat = state.get('combat') or {}; player = combat.get('player') or {}
    ready = combat.get('action_readiness') or {}
    if not ready.get('can_use_combat_actions') or not ready.get('snapshot_stable'):
        return {**report, 'reason': 'unsettled_or_stale'}
    if player.get('energy', 0) <= 0 or player.get('cards_played_this_turn', 0) > 0:
        return report
    hp = player.get('current_hp'); run_hp = (state.get('run') or {}).get('current_hp')
    if not isinstance(hp, int) or hp != run_hp:
        return {**report, 'reason': 'hp_mismatch'}
    if hp <= danger_hp:
        return {**report, 'reason': 'baseline_current_hp', 'hp': hp}
    enemies = [e for e in combat.get('enemies', []) if e.get('is_alive')]
    attackers = []
    for enemy in enemies:
        damage = 0
        for intent in enemy.get('intents', []):
            if intent.get('intent_type') != 'Attack':
                continue
            total = intent.get('total_damage')
            if not isinstance(total, int) or total < 0:
                return {**report, 'reason': 'unknown_attack_total'}
            damage += total
        if damage:
            attackers.append((enemy, damage))
    hand = combat.get('hand', [])
    # This is an abstention, not a claim that the card will kill. Unknown
    # multi-hit, target modifiers and triggers can only enlarge this set.
    for enemy, _ in attackers:
        for card in hand:
            if not card.get('playable') or enemy['index'] not in card.get('valid_target_indices', []):
                continue
            preview = _value(card, 'Damage')
            if preview is not None and preview >= enemy['current_hp'] + enemy.get('block', 0):
                return {**report, 'reason': 'possible_immediate_attacker_kill',
                        'enemy_index': enemy['index'], 'card_index': card['index']}
    incoming = sum(damage for _, damage in attackers)
    block = player.get('block', 0)
    block += sum(p.get('amount', 0) for p in player.get('powers', []) if p.get('power_id') == 'PLATING_POWER')
    if any(r.get('relic_id') == 'CLOAK_CLASP' for r in (state.get('run') or {}).get('relics', [])):
        block += len(hand)  # optimistic: cards played later can reduce this
    beckon = beckon_endturn_projection(state)
    if beckon and not beckon['known']:
        return {**report, 'reason': 'unknown_beckon_loss'}
    self_loss = beckon['retained_hp_loss'] if beckon else 0
    forecast_loss = max(0, incoming - block) + self_loss
    projected_hp = hp - forecast_loss
    review = forecast_loss >= min_loss and projected_hp <= danger_hp
    return {**report, 'review': review,
            'reason': 'projected_large_hp_loss' if review else 'below_review_threshold',
            'hp': hp, 'energy': player['energy'], 'incoming': incoming,
            'block': block, 'known_self_loss': self_loss,
            'forecast_loss': forecast_loss, 'projected_hp': projected_hp,
            'attackers': [e['index'] for e, _ in attackers]}
