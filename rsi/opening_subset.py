"""E169 explicit discard/redraw domain; no inferred engine lifecycle API."""
from .subset_action import contract
from .trace import digest


def opening_domain(state,entry_command,previous_state):
    c=state.get('context') or {};before=previous_state.get('context') or {}
    if (state.get('decision')!='card_select' or entry_command.get('action')!='select_map_node'
            or previous_state.get('decision')!='map_select'
            or c.get('room_type') not in ('Monster','Elite','Boss')
            or (c.get('act'),c.get('floor'))==(before.get('act'),before.get('floor'))):
        raise ValueError('Not an observed pre-play combat-node selection')
    relics=state.get('player',{}).get('relics',[])
    if not any(r.get('name')=='Gambling Chip' for r in relics):
        raise ValueError('No Gambling Chip evidence')
    domain=contract(state)
    if domain['min_select']!=0 or domain['max_select']!=len(state['cards']):
        raise ValueError('Expected optional whole-hand discard/redraw')
    if domain['legal_subsets']>32:raise ValueError('Opening search supports at most 32 subsets')
    return dict(**domain,effect='discard_and_redraw',
        evidence='Registered Gambling Chip pre-play roots; other simultaneous opening effects are not inferred')


def indexes(choice):
    args=choice['action'].get('args',{})
    return [args['card_index']] if 'card_index' in args else [int(x) for x in args.get('indices','').split(',') if x]


def candidate_id(choice):
    return digest(choice['action'])[:16]


def rank(result):
    if result.get('error') or result['status'] not in ('clear','defeat'):
        raise ValueError('Incomplete/invalid rollout has no terminal rank')
    # Dead inventory is not a survival improvement.
    return (1,result['hp'],len(result['potions'])) if result['status']=='clear' else (0,0,0)


def pick(records):
    if not records:raise ValueError('Empty candidate set')
    # Stable independent of completion order; choose the least discard on ties.
    ordered=sorted(records,key=lambda r:(len(r['discard_indices']),r['discard_indices']))
    return max(ordered,key=rank)
