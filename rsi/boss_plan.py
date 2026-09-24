"""Exact-entry, one-room Astra guidance for a headless Boss replay."""

from .trace import digest


REQUIRED = {'case_id', 'entry_state_hash', 'act', 'floor', 'boss_id',
            'max_potions', 'guidance'}


def validate_boss_plan(plan, state):
    if not isinstance(plan, dict) or set(plan) != REQUIRED:
        raise ValueError('Invalid Boss plan schema')
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
