"""Exact-entry, one-room Astra guidance for a headless Boss replay."""

from .trace import digest


REQUIRED = {'case_id', 'entry_state_hash', 'act', 'floor', 'boss_id',
            'max_potions', 'guidance'}


def validate_boss_plan(plan, state, require_directives=False):
    allowed = REQUIRED | {'opening_actions'}
    if not isinstance(plan, dict) or not REQUIRED <= set(plan) or not set(plan) <= allowed:
        raise ValueError('Invalid Boss plan schema')
    directives = plan.get('opening_actions')
    if require_directives and not directives:
        raise ValueError('Typed Boss policy requires opening actions')
    if directives is not None:
        if not isinstance(directives, list) or not 1 <= len(directives) <= 3:
            raise ValueError('Boss opening actions must have length 1..3')
        for directive in directives:
            if not isinstance(directive, dict) or directive.get('kind') not in ('potion', 'card'):
                raise ValueError('Invalid Boss opening directive')
            fields = ({'kind', 'potion_name'} if directive['kind'] == 'potion'
                      else {'kind', 'card_id'})
            if not fields <= set(directive) or not set(directive) <= fields | {'target_name'}:
                raise ValueError('Invalid Boss opening directive fields')
            if any(not isinstance(v, str) or not v for k, v in directive.items() if k != 'kind'):
                raise ValueError('Invalid Boss opening directive value')
    if not isinstance(plan['guidance'], str) or not 1 <= len(plan['guidance']) <= 1200:
        raise ValueError('Boss guidance must be 1..1200 characters')
    if not isinstance(plan['max_potions'], int) or not 0 <= plan['max_potions'] <= 3:
        raise ValueError('Boss potion budget must be 0..3')
    context = state.get('context') or {}
    boss = context.get('boss') or {}
    if (state.get('decision') != 'combat_play' or context.get('room_type') != 'Boss'
            or context.get('act') != plan['act'] or context.get('floor') != plan['floor']
            or boss.get('id') != plan['boss_id'] or digest(state) != plan['entry_state_hash']):
        raise ValueError('Boss plan does not match the exact room entry state')
    return plan


def resolve_opening_action(directive, state, choices):
    """Resolve semantic names against a freshly observed legal action set."""
    matching = []
    for choice in choices:
        action = choice['action']
        args = action.get('args') or {}
        if directive['kind'] == 'potion':
            if action.get('action') != 'use_potion' or choice.get('name') != directive['potion_name']:
                continue
        else:
            if action.get('action') != 'play_card':
                continue
            card = next((c for c in state.get('hand', []) if c['index'] == args.get('card_index')), None)
            if card is None or card.get('id') != directive['card_id']:
                continue
        target = args.get('target_index')
        desired = directive.get('target_name')
        if desired is None and target is not None:
            continue
        if desired is not None:
            enemy = next((e for e in state.get('enemies', []) if e['index'] == target), None)
            if enemy is None or enemy.get('name') != desired:
                continue
        matching.append(choice)
    if len(matching) != 1:
        raise ValueError(f'Boss opening directive resolved to {len(matching)} legal actions')
    return matching[0]


def plan_active(plan, state):
    if plan is None or state.get('decision') not in ('combat_play', 'card_select'):
        return False
    context = state.get('context') or {}
    return (context.get('act') == plan['act'] and context.get('floor') == plan['floor']
            and context.get('room_type') == 'Boss')


def decision_context(plan, state, planning, potions_used):
    return {
        'scope': f"Boss room Act {plan['act']} floor {plan['floor']}",
        'boss_id': plan['boss_id'],
        'astra_guidance': plan['guidance'],
        'potion_budget_remaining': plan['max_potions'] - potions_used,
        'computed_proposal': planning,
        'instruction': 'Choose one legal current action that advances the room plan. The state and planner proposal are current; the plan was authored at room entry and may be stale on details. Recheck current enemies, powers, hand and intents. The controller will replan after your action.',
    }
