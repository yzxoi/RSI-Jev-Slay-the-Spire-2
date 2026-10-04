"""Short observable campaign transactions; unexpected transitions invalidate the queue."""
from collections import Counter
import copy
from .engine import action
from .trace import digest

SHOP={'buy_card':'cards','buy_potion':'potions'}


def card_key(card,shop=False,face=False):
    return digest(dict(id=None if face else card.get('id'),name=card.get('name'),type=card.get('type'),
        cost=card.get('card_cost') if shop else card.get('cost'),upgraded=bool(card.get('upgraded')),
        stats=card.get('stats'),description=card.get('description')))


def counts(items,key):return Counter(key(x) for x in items)


def owned_rules(state,rules):
    ids={p['id'] for p in state.get('player',{}).get('potions',[])}
    return [r for r in rules if r['potion_id'] in ids]


def automatic(state,choices):
    if state['decision']=='potion_reward' and state.get('can_claim') and state['player'].get('has_open_potion_slots'):
        return next((c for c in choices if c['action']['action']=='claim_potion_reward'),None)
    routes=[c for c in choices if c['action']['action']=='select_map_node']
    other=[c for c in choices if c not in routes]
    if (state['decision']=='map_select' and len(routes)==1
            and state['player']['hp']>state['player']['max_hp']*.5
            and all(c['action']['action']=='use_potion' and c.get('name')=='Blood Potion' for c in other)):
        return routes[0]
    return None


def selection_kind(chosen):
    a=chosen['action']['action'];d=chosen.get('details') or {}
    if a=='remove_card':return 'remove'
    if a=='choose_option':
        if d.get('option_id')=='SMITH':return 'upgrade'
        if d.get('text_key')=='SAPPHIRE_SEED.pages.INITIAL.options.EAT':return 'upgrade_heal'
        if d.get('text_key')=='SYMBIOTE.pages.INITIAL.options.KILL_WITH_FIRE':return 'transform'
    return None


def offer_key(offer):
    return digest({k:v for k,v in offer.items() if k not in ('can_buy','is_stocked')})


def catalog(state):
    return {key:[(x['index'],offer_key(x) if x.get('is_stocked') else None,bool(x.get('is_stocked'))) for x in state.get(key,[])]
            for key in ('cards','potions','relics')}


class Transaction:
    """Steps contain only visible shop offers or references into the entry deck.

    Never continue across a combat/room boundary, random-card generation or relic
    purchase. The initial action is expert-owned; each later action is revalidated.
    """
    def __init__(self,state,first,steps):
        if not isinstance(steps,list) or len(steps)>5:raise ValueError('Transaction must have <=5 followups')
        self.context=copy.deepcopy(state.get('context'));self.steps=[];self.pending=None
        self.invalid=None;self.last=first;self.removal_price=state.get('card_removal_cost')
        self.shop_catalog=catalog(state) if state['decision']=='shop' else None
        previous=first;last_selection=None
        for step in steps:
            if not {'kind','index','potion_reservations'}<=set(step) or set(step)-{'kind','index','potion_reservations','acquire_reservation'}:
                raise ValueError('Unknown transaction fields')
            kind=step['kind'];compiled=copy.deepcopy(step)
            if kind in SHOP:
                if type(step['index']) is not int:raise ValueError('Offer index must be an integer')
                if self.shop_catalog is None:raise ValueError('Shop step outside visible shop')
                offers=[x for x in state[SHOP[kind]] if x['index']==step['index'] and x.get('is_stocked')]
                if len(offers)!=1:raise ValueError('Offer unavailable at entry')
                compiled['offer_key']=offer_key(offers[0])
            elif kind=='select_deck_card':
                if selection_kind(previous) is None:raise ValueError('Selection is not a known deck operation')
                last_selection=selection_kind(previous)
                i=step['index'];deck=state['player']['deck']
                if type(i) is not int or not 0<=i<len(deck):raise ValueError('Invalid entry deck reference')
                compiled['card_key']=card_key(deck[i])
                compiled['occurrence']=sum(card_key(c)==compiled['card_key'] for c in deck[:i])
            elif kind not in ('remove_card','leave_room') or self.shop_catalog is None:
                raise ValueError('Unsupported transaction step')
            if previous['action']['action'] in ('buy_relic','leave_room') or (previous['action']['action']=='select_cards' and last_selection!='remove'):
                raise ValueError('Transaction must stop after opaque/final action')
            self.steps.append(compiled)
            previous=dict(action=action('select_cards' if kind=='select_deck_card' else kind))
        self.initial_hash=digest(state);self.expected_hash=self.initial_hash

    def invalidate(self,reason):
        self.steps=[];self.pending=None;self.invalid=reason

    def accepted(self,before,chosen,after):
        if not self.steps:self.pending=None;return
        if digest(before)!=self.expected_hash:
            self.invalidate('stale_before_state');return
        if after.get('context')!=self.context:
            self.invalidate('room_changed');return
        a=chosen['action']['action'];bp=before['player'];ap=after['player']
        expected_gold=bp['gold'];deck=counts(bp.get('deck',[]),card_key)
        potions=counts(bp.get('potions',[]),lambda p:p['id'])
        expected_hp=bp['hp'];kind=selection_kind(chosen);purchase_face=None
        if a in SHOP:
            idx=chosen['action']['args'][('card' if a=='buy_card' else 'potion')+'_index']
            offer=next(x for x in before[SHOP[a]] if x['index']==idx)
            expected_gold-=offer['cost']
            if a=='buy_card':purchase_face=card_key(offer,shop=True,face=True)
            else:potions[offer['id']]+=1
            if self.shop_catalog is not None:
                self.shop_catalog[SHOP[a]]=[(i,None if i==idx else k,False if i==idx else stock) for i,k,stock in self.shop_catalog[SHOP[a]]]
        elif kind in ('remove','upgrade','upgrade_heal','transform'):
            if after['decision']!='card_select':self.invalidate('selection_not_opened');return
            if kind=='upgrade_heal':expected_hp=min(bp['max_hp'],bp['hp']+(chosen['details'].get('vars') or {})['Heal'])
        elif a=='select_cards' and selection_kind(self.last)=='remove':
            indexes=[int(x) for x in chosen['action']['args']['indices'].split(',')]
            for i in indexes:deck[card_key(next(c for c in before['cards'] if c['index']==i))]-=1
            expected_gold-=self.removal_price
        else:
            self.invalidate('opaque_transition');return
        actual_deck=counts(ap.get('deck',[]),card_key)
        deck_ok=actual_deck==+deck
        if purchase_face is not None:
            added=actual_deck-deck;removed=deck-actual_deck
            deck_ok=(not removed and sum(added.values())==1 and any(
                card_key(c) in added and card_key(c,face=True)==purchase_face for c in ap.get('deck',[])))
        ok=(ap['gold']==expected_gold and ap['hp']==expected_hp and ap['max_hp']==bp['max_hp']
            and ap.get('potion_capacity')==bp.get('potion_capacity') and ap.get('relics')==bp.get('relics')
            and deck_ok and counts(ap.get('potions',[]),lambda p:p['id'])==+potions)
        if after['decision']=='shop':ok=ok and catalog(after)==self.shop_catalog
        if not ok:self.invalidate('unexpected_inventory_or_offer_change');return
        self.last=chosen;self.expected_hash=digest(after)

    def choose(self,state,choices):
        if not self.steps:return None
        if digest(state)!=self.expected_hash:self.invalidate('stale_current_state');return None
        if state.get('context')!=self.context:self.invalidate('room_changed');return None
        step=self.steps[0];kind=step['kind'];selected=None
        if kind=='select_deck_card' and state['decision']=='card_select' and state.get('min_select')==state.get('max_select')==1:
            matches=[c for c in state['cards'] if card_key(c)==step['card_key']]
            if len(matches)>step['occurrence']:
                idx=matches[step['occurrence']]['index']
                cmd=action('select_cards',indices=str(idx))
                selected=next((c for c in choices if c['action']==cmd),None)
                if selected is None and not choices:
                    from .subset_action import contract,resolve
                    selected=resolve(contract(state),[idx],digest(state))
        elif state['decision']=='shop':
            if catalog(state)!=self.shop_catalog:self.invalidate('offer_changed');return None
            for c in choices:
                if c['action']['action']!=kind:continue
                if kind in SHOP:
                    idx=c['action']['args'][('card' if kind=='buy_card' else 'potion')+'_index']
                    if idx!=step['index'] or offer_key(c['details'])!=step['offer_key']:continue
                selected=c;break
        if selected is None:self.invalidate('fresh_choice_unavailable');return None
        self.steps.pop(0);self.pending=step
        return selected,step['potion_reservations']
