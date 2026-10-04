"""Offline ownership evidence from wire neighbors, never the controller's flag.

The CLI serializes pending selections before testing CombatManager.IsInProgress.
For observed menus use the bracketing stable phases and triggering wire action.
An unfinished room-entry selection needs explicit room-entry evidence; unknown
sequences fail audit instead of receiving a convenient campaign label.
"""
from .trace import digest


def selection(state):
    return state.get('decision')=='card_select' or (
        state.get('decision')=='card_reward' and state.get('from_event'))


def labels(pairs):
    rows=[]
    for i,(command,state) in enumerate(pairs):
        if not selection(state):continue
        before=next((s for _,s in reversed(pairs[:i]) if s.get('decision') and not selection(s)),{})
        after=next((s for _,s in pairs[i+1:] if s.get('decision') and not selection(s)),{})
        b,a=before.get('decision'),after.get('decision')
        if b=='combat_play':owner='battle';evidence='previous_play_phase'
        elif a=='combat_play':owner='battle';evidence='next_play_phase'
        elif b in ('event_choice','rest_site','shop','card_reward','potion_reward','treasure'):
            owner='campaign';evidence='campaign_trigger'
        elif (b=='map_select' and command.get('action')=='select_map_node'
              and state.get('context',{}).get('room_type') in ('Monster','Elite','Boss') and a is None):
            owner='battle';evidence='unfinished_combat_node_entry'
        else:raise ValueError(f'Unlabelled selection at wire command {i+1}: {b} -> {a}')
        rows.append(dict(command_number=i+1,state_hash=digest(state),expected_owner=owner,
            evidence=evidence,previous_phase=b,next_phase=a,trigger=command,context=state.get('context')))
    return rows


def campaign_request_failures(events,pairs):
    battle_hashes={r['state_hash'] for r in labels(pairs) if r['expected_owner']=='battle'}
    battle_hashes.update(digest(s) for _,s in pairs if s.get('decision')=='combat_play')
    return [dict(seq=e['data']['seq'],state_hash=e['data']['state_hash']) for e in events
            if e['kind']=='campaign_request' and e['data']['state_hash'] in battle_hashes]
