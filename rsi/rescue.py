"""Conservative supported-potion comparisons; forecasts remain approximate."""
import copy
import re
from .planner import choose_plan
from .policy import combat_candidates
from .potions import with_potions
from .numerical import intent_damage

ENERGY_UNLOCK = {'STRIKE_IRONCLAD','DEFEND_IRONCLAD','BASH','SHRUG_IT_OFF','IRON_WAVE',
                 'POMMEL_STRIKE','STRIKE_SILENT','DEFEND_SILENT','STRIKE_DEFECT','DEFEND_DEFECT',
                 'STRIKE_REGENT','DEFEND_REGENT','STRIKE_NECROBINDER','DEFEND_NECROBINDER'}
DAMAGE_GUARDS = {'INTANGIBLE','INVINCIBLE','SLIPPERY','BUFFER','HARD_TO_KILL','REFLECT'}


def key(name):return re.sub(r'[^A-Z0-9]+','_',str(name).upper()).strip('_')


def projected_loss(state, plan):
    hp=plan['predicted_enemy_hp']
    incoming=sum(intent_damage(e) for e in state.get('enemies',[]) if hp.get(e['index'],0)>0)
    return max(0,incoming-plan['predicted_block']-state.get('player',{}).get('end_turn_block',0))


def rescue_choice(state, choices, baseline=None):
    selected, plan = baseline or choose_plan(state,choices)
    loss=projected_loss(state,plan);player_hp=state['player']['hp'];forecasts=[];supported=[]
    potion_choices=[c for c in with_potions(state,choices) if c['action']['action']=='use_potion']
    for candidate in potion_choices:
        potion=candidate['details'];name=key(potion.get('potion_id',potion['name']));v=potion.get('vars') or {};v={k.lower():x for k,x in v.items()};shadow=copy.deepcopy(state);effect=None
        if name=='BLOCK_POTION' and isinstance(v.get('block'),(int,float)):
            shadow['player']['block']+=max(0,v['block']);effect={'block':max(0,v['block'])}
        elif name=='ENERGY_POTION' and isinstance(v.get('energy'),(int,float)):
            shadow['energy']+=max(0,v['energy']);effect={'energy':max(0,v['energy']),'unlocked_indices':[]}
            for card in shadow.get('hand',[]):
                ident=card['id'].split('.')[-1]
                if (ident in ENERGY_UNLOCK and card.get('cost',0)>state['energy'] and card['cost']<=shadow['energy'] and not set(card.get('keywords') or []) & {'Unplayable'}):
                    card['can_play']=True;effect['unlocked_indices'].append(card['index'])
        elif name in {'FIRE_POTION','EXPLOSIVE_POTION'} and isinstance(v.get('damage'),(int,float)):
            target=candidate['action']['args'].get('target_index');targets=[e for e in shadow['enemies'] if target is None or target==e['index']]
            if any(key(p.get('name',p.get('power_id',''))).removesuffix('_POWER') in DAMAGE_GUARDS for e in targets for p in e.get('powers') or []):continue
            for enemy in targets:
                damage=max(0,v['damage']);absorbed=min(enemy.get('block',0),damage);enemy['block']=enemy.get('block',0)-absorbed;enemy['hp']=max(0,enemy['hp']-damage+absorbed)
            effect={'power_damage':max(0,v['damage']),'targets':[e['index'] for e in targets]}
        if effect is None:continue
        _, forecast=choose_plan(shadow,combat_candidates(shadow));after=projected_loss(shadow,forecast)
        saved=loss-after;saves_lethal=loss>=player_hp and after<player_hp
        entry={'candidate_id':candidate['id'],'potion':name,'effect':effect,'predicted_loss_before':loss,'predicted_loss_after':after,'predicted_hp_saved':saved,'avoids_predicted_lethal':saves_lethal}
        forecasts.append(entry)
        if saves_lethal or saved>=8:supported.append(((saves_lethal,saved),candidate,entry))
    chosen=max(supported,key=lambda row:row[0]) if supported else None
    return (chosen[1] if chosen else selected),{'scope':'Approximate current-hand comparison; does not model future draws, most triggers or potion opportunity cost. Only supplied supported potion values are used.','baseline_plan':plan,'baseline_loss':loss,'forecasts':forecasts,'override':chosen[2] if chosen else None}
