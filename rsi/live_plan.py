"""Adapt native previews to the approximate E012 planning schema."""
import math
from .planner import choose_plan


def normalize(raw):
    combat=raw['combat'];p=combat['player'];deck={c['card_id']:c for c in raw['run']['deck']}
    def power(entity,key):return sum(x.get('amount',0) for x in entity.get('powers',[]) if x.get('power_id')==key)
    strength=power(p,'STRENGTH_POWER');weak=.75 if power(p,'WEAK_POWER') else 1
    enemies=[{'index':e['index'],'hp':e['current_hp'],'block':e['block'],'intents':[{'total_damage':i.get('total_damage') or 0,'damage':i.get('damage') or 0,'hits':i.get('hits') or 1} for i in e['intents']],'powers':e['powers'],'native_slippery':power(e,'SLIPPERY_POWER')} for e in combat['enemies'] if e.get('is_alive')]
    hand=[]
    for card in combat['hand']:
        stats={v['name'].lower():v.get('current_value',v['base_value']) for v in card.get('dynamic_values',[])}
        kind=deck.get(card['card_id'],{}).get('card_type',card.get('card_type','Skill'))
        previews=[]
        targets=card.get('valid_target_indices',[]) if card.get('requires_target') else [e['index'] for e in enemies]
        base=stats.get('calculateddamage',stats.get('damage',0))
        if card['card_id']=='BODY_SLAM':base=p['block']
        if base or card['card_id']=='BODY_SLAM':
            for e in combat['enemies']:
                if e['index'] not in targets:continue
                vulnerable=1.5 if power(e,'VULNERABLE_POWER') else 1
                # current_value already includes owner strength/weak in native preview.
                slow_count=p.get('cards_played_this_turn',0) if power(e,'SLOW_POWER') else None
                native_base=max(0,base)*vulnerable
                damage=math.floor(native_base*(1+.1*slow_count if slow_count is not None else 1))
                hits=2 if card['card_id']=='TWIN_STRIKE' else max(1,int(stats.get('repeat',stats.get('hits',1))))
                previews.append({'target_index':e['index'],'damage':damage,'total_damage':damage*hits,'native_hits':hits,'native_base_damage':native_base,'native_target_multiplier':vulnerable,'native_slow_count':slow_count,'hp_damage_cap':1 if power(e,'SLIPPERY_POWER') else None})
        # Block preview already includes dexterity/frail; do not apply twice.
        hand.append({'index':card['index'],'id':card['card_id'],'name':card['name'],'cost':card['energy_cost'],'type':kind,'stats':stats,'damage_by_target':previews,'can_play':card['playable'],'target_type':card['target_type']})
    return {'energy':p['energy'],'player':{'hp':p['current_hp'],'block':p['block'],'end_turn_block':power(p,'PLATING_POWER')},'hand':hand,'enemies':enemies}


def plan_native(raw,cs):
    plays=[c for c in cs if c['action']['action'] in ['play_card','end_turn']]
    state=normalize(raw);selected,plan=choose_plan(state,plays)
    plan['native_preview_limit']='Native current_value already includes owner modifiers; CalculatedDamage supported. Target vulnerability has integer rounding limits. Slow uses prior cards played in this single-player turn; Slippery HP cap is tracked. Other triggers, fractional preview rounding and multi-hit effects remain approximate.'
    return selected,plan
