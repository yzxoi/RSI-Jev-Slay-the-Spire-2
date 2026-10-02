"""Opt-in complete PPO menus; default Jev/live candidate limits stay unchanged."""
import math

from .battle_search import choices_for, baseline_choice, CONTROL
from .full import macro_candidates
from .teacher import selection_choice

ACTION_SPACE = 'e136-complete-subsets-v1'
ACTION_LIMIT = 4096


def complete_choices(state):
    if state.get('decision') != 'card_select':
        return choices_for(state)
    n = len(state.get('cards', []))
    lo, hi = state.get('min_select', 1), state.get('max_select', 1)
    total = sum(math.comb(n, k) for k in range(lo, min(n, hi) + 1))
    if not 0 < total <= ACTION_LIMIT:
        raise ValueError(f'Complete selection resource bound: {total} > {ACTION_LIMIT}')
    result = macro_candidates(state, resource_decisions=True, selection_cap=ACTION_LIMIT)
    if len(result) != total:
        raise ValueError('Incomplete legal selection enumeration')
    return result


def complete_baseline(state, choices, previous):
    if state.get('decision') == 'card_select':
        return selection_choice(state, choices, CONTROL, previous)
    return baseline_choice(state, previous)
