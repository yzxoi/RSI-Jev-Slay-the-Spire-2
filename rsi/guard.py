"""Conservative exclusion of clearly dominated basic-card end turns."""
import re
from .numerical import intent_damage

SAFE_POWERS={'STRENGTH','DEXTERITY','WEAK','VULNERABLE','FRAIL','SLOW','NO_DRAW','CLARITY','POISON','REGEN','REGENERATION','BUFFER','INTANGIBLE','RITUAL'}

def key(power):
    value=power.get('power_id') or power.get('id') or power.get('name','')
    value=value.split('.')[-1].upper().replace(' ','_')
    return re.sub(r'_?POWER$','',value)


def filter_end_turn(state,candidates):
    native='combat' in state
    if native:
        combat=state['combat'];p=combat['player'];hand=combat['hand'];enemies=[e for e in combat['enemies'] if e.get('is_alive')];powers=p.get('powers') or [];relics=state['run'].get('relics',[]);energy=p['energy'];block=p['block']
    else:
        p=state.get('player',{});hand=state.get('hand',[]);enemies=state.get('enemies',[]);powers=state.get('player_powers') or [];relics=p.get('relics',[]);energy=state.get('energy',0);block=p.get('block',0)
    report={'excluded':False,'reason':'no_proven_basic_card_improvement'}
    allpowers=powers+[power for e in enemies for power in e.get('powers') or []]
    unknown=[key(x) for x in allpowers if key(x) not in SAFE_POWERS]
    # Unknown powers can punish plays or retain energy. Pain triggers from hand.
    if unknown or any('ICE_CREAM' in str(r).upper().replace(' ','_') for r in relics) or any((c.get('card_id') or c.get('id','')).split('.')[-1] in {'PAIN','NORMALITY'} for c in hand):
        report.update(reason='unknown_or_card_play_downside',unknown_powers=unknown);return candidates,report
    byindex={c['index']:c for c in hand};incoming=sum(intent_damage(e) for e in enemies)
    useful=[]
    for choice in candidates:
        cmd=choice['action'];args=cmd.get('args',cmd)
        if cmd['action']!='play_card':continue
        c=byindex[args['card_index']];ident=(c.get('card_id') or c.get('id','')).split('.')[-1];cost=c.get('energy_cost',c.get('cost',0))
        if cost>energy:continue
        if native:stats={v['name'].lower():v.get('current_value',v.get('base_value',0)) for v in c.get('dynamic_values',[])}
        else:stats=c.get('stats') or {}
        if ident.startswith('DEFEND_') and stats.get('block',0)>0 and incoming>block:useful.append(choice['id'])
        if ident.startswith('STRIKE_'):
            target=args.get('target_index');enemy=next((e for e in enemies if e['index']==target),None)
            if not enemy:continue
            damage=stats.get('damage',0) if native else next((v.get('total_damage',v.get('damage',0)) or 0 for v in c.get('damage_by_target',[]) if v['target_index']==target),0)
            if damage>enemy.get('block',0):useful.append(choice['id'])
    if useful:
        report.update(excluded=True,reason='legal_basic_card_has_positive_immediate_value',witness_ids=useful,incoming=incoming,block=block,energy=energy)
        return [c for c in candidates if c['action']['action']!='end_turn'],report
    return candidates,report
