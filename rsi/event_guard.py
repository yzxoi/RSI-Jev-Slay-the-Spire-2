"""Bound irreversible HP spending in native event choices."""


def bound_bridge_reroll(raw, offered):
    """Allow the first Slippery Bridge reroll, then preserve the exit choice.

    The event's stable option text key advances from HOLD_ON_0 after each
    reroll. Its later HOLD_ON_LOOP key does not expose a count, so a one-reroll
    cap avoids depending on localized cost text or a mutable history object.
    """
    event = raw.get('event') or {}
    if raw.get('screen') != 'EVENT' or event.get('event_id') != 'SLIPPERY_BRIDGE':
        return offered, None
    rerolls = [choice for choice in offered
               if '.options.HOLD_ON_' in (choice.get('details') or {}).get('text_key', '')]
    if not rerolls:
        return offered, {'event_id': 'SLIPPERY_BRIDGE', 'excluded': False,
                         'reason': 'no_reroll_candidate'}
    later = [choice for choice in rerolls
             if not (choice.get('details') or {}).get('text_key', '').endswith('.options.HOLD_ON_0')]
    kept = [choice for choice in offered if choice not in later]
    if not later or not kept:
        return offered, {'event_id': 'SLIPPERY_BRIDGE', 'excluded': False,
                         'reason': 'first_reroll_or_no_exit'}
    return kept, {'event_id': 'SLIPPERY_BRIDGE', 'excluded': True,
                  'reason': 'one_reroll_hp_cap',
                  'excluded_actions': [choice['action'] for choice in later]}
