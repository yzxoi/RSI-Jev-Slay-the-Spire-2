"""One advisory reconsideration; action space and observed state stay unchanged."""
import copy

from .end_turn_check import arithmetic


def recheck_gate(state, proposal, candidates):
    if (state.get('decision') != 'combat_play' or state.get('energy', 0) <= 0
            or proposal['action']['action'] != 'end_turn'):
        return {'eligible': False, 'reason': 'not_positive_energy_end_turn'}
    allowed_indices = {c['action'].get('args', {}).get('card_index') for c in candidates
                       if c['action']['action'] == 'play_card'}
    preview_state = {**state, 'hand': [c for c in state['hand'] if c['index'] in allowed_indices]}
    preview = arithmetic(preview_state, plating=True)
    preview.pop('seconds')
    return {'eligible': preview['flags_missed_defense'], 'reason': 'limited_defense_preview', 'preview': preview}


def review_payload(payload, proposal, gate):
    result = copy.deepcopy(payload)
    result['end_turn_review'] = {
        'proposed_choice': proposal['id'], 'preview': gate['preview'],
        'objective': 'Before ending, reassess whether a remaining legal defense is worth playing to avoid the predicted HP loss.',
        'limitations': 'This is a conditional arithmetic preview, not a simulation or proof. It ignores unmodeled triggers, card-play penalties, discard/draw changes and future value. Use the complete current rules and state. You may keep end_turn if the other choices are worse. This is your only reconsideration at this decision.'}
    return result


def act1_clear(state, boss_entered):
    if not boss_entered or state.get('player', {}).get('hp', 0) <= 0:
        return False
    decision = state.get('decision')
    if decision == 'card_reward':
        return not state.get('from_event') and 'gold_earned' in state
    return decision in ('potion_reward', 'map_select')
