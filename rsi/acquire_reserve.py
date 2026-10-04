"""Bind a potion reservation to one verified acquisition, without extra expert calls."""
from collections import Counter
import copy
from .trace import digest


def prepare(state, chosen, rule):
    if rule is None:return None
    if (not isinstance(rule,dict) or set(rule)!={'potion_id','until','release_hp_fraction'}
            or not isinstance(rule['potion_id'],str) or not rule['potion_id']
            or rule['until'] not in ('Elite','Boss')
            or type(rule['release_hp_fraction']) not in (int,float)
            or not 0<=rule['release_hp_fraction']<=.5):
        raise ValueError('Invalid acquisition reservation')
    command=chosen['action'];kind=command['action'];price=None
    if kind=='buy_potion' and state['decision']=='shop':
        offers=[p for p in state['potions'] if p['index']==command['args']['potion_index']]
        if len(offers)!=1:raise ValueError('Acquisition offer missing/ambiguous')
        offer=offers[0];price=offer['cost']
        if not offer.get('is_stocked') or not offer.get('can_buy') or price>state['player']['gold']:
            raise ValueError('Acquisition unavailable')
    elif kind=='claim_potion_reward' and state['decision']=='potion_reward' and state.get('can_claim'):
        offer=state['potion']
    else:raise ValueError('Reservation requires an immediate legal buy or claim')
    if not state['player'].get('has_open_potion_slots') or offer.get('id')!=rule['potion_id']:
        raise ValueError('Acquisition ID/slot mismatch')
    return dict(before_hash=digest(state),action_hash=digest(command),rule=copy.deepcopy(rule),price=price)


def confirm(intent, before, chosen, after, reservations):
    if intent is None:return reservations
    if intent['before_hash']!=digest(before) or intent['action_hash']!=digest(chosen['action']):
        raise ValueError('Stale acquisition transaction')
    count=lambda s:Counter(p['id'] for p in s['player'].get('potions',[]))
    expected=count(before);expected[intent['rule']['potion_id']]+=1
    if count(after)!=expected:raise ValueError('Acquisition inventory delta unconfirmed')
    if intent['price'] is not None and before['player']['gold']-after['player']['gold']!=intent['price']:
        raise ValueError('Acquisition payment unconfirmed')
    # Match E160 semantics: one rule covers all current copies, independent of slot/index shifts.
    return [copy.deepcopy(r) for r in reservations if r['potion_id']!=intent['rule']['potion_id']]+[copy.deepcopy(intent['rule'])]
