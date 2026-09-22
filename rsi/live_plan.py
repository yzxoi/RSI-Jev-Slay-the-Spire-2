"""Adapt native previews to the approximate E012 planning schema."""
import math
from .planner import choose_plan


def normalize(raw):
    combat=raw['combat'];p=combat['player'];deck={c['card_id']:c for c in raw['run']['deck']}
    def power(entity,key):return sum(x.get('amount',0) for x in entity.get('powers',[]) if x.get('power_id')==key)
    strength=power(p,'STRENGTH_POWER');weak=.75 if power(p,'WEAK_POWER') else 1
    enemies=[{'index':e['index'],'hp':e['current_hp'],'block':e['block'],'intents':[{'total_damage':i.get('total_damage') or 0,'damage':i.get('damage') or 0,'hits':i.get('hits') or 1} for i in e['intents']],'powers':e['powers']} for e in combat['enemies'] if e.get('is_alive')]
    hand=[]
    for card in combat['hand']:
        stats={v['name'].lower():v.get('current_value',v['base_value']) for v in card.get('dynamic_values',[])}
        kind=deck.get(card['card_id'],{}).get('card_type',card.get('card_type','Skill'))
        previews=[]
        targets=card.get('valid_target_indices',[]) if card.get('requires_target') else [e['index'] for e in enemies]
        base=stats.get('damage',0)
        if card['card_id']=='BODY_SLAM':base=p['block']
        if base or card['card_id']=='BODY_SLAM':
            for e in combat['enemies']:
                if e['index'] not in targets:continue
                vulnerable=1.5 if power(e,'VULNERABLE_POWER') else 1
                damage=math.floor(max(0,base+strength)*weak*vulnerable)
                previews.append({'target_index':e['index'],'damage':damage})
        # Native dynamic block is a base preview; model known global modifiers.
        if stats.get('block'):
            stats['block']=math.floor(max(0,stats['block']+power(p,'DEXTERITY_POWER'))*(.75 if power(p,'FRAIL_POWER') else 1))
        hand.append({'index':card['index'],'id':card['card_id'],'name':card['name'],'cost':card['energy_cost'],'type':kind,'stats':stats,'damage_by_target':previews,'can_play':card['playable'],'target_type':card['target_type']})
    return {'energy':p['energy'],'player':{'hp':p['current_hp'],'block':p['block']},'hand':hand,'enemies':enemies}


def plan_native(raw,cs):
    plays=[c for c in cs if c['action']['action'] in ['play_card','end_turn']]
    state=normalize(raw);selected,plan=choose_plan(state,plays)
    plan['native_preview_limit']='Damage modifiers approximate; no full native combat simulator. Unknown mechanics remain heuristics.'
    return selected,plan
