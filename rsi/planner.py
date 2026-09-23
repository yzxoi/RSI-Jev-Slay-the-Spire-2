"""Bounded approximate turn planning; only execute the first fresh legal action."""
import copy
import math
from .numerical import intent_damage
from . import triggers as trigger_rules
from .retaliation import thorns_before_hit, hit_count

SCOPE='Approximate current-hand search, not an engine clone. Known No Draw/Battle Trance locks later draw utility; drawn cards, random effects, orbs, minions, triggers and unknown mechanics remain unmodeled. Re-evaluate after each real action.'


def _no_draw_active(state):
    powers=(state.get('player',{}).get('powers') or [])+(state.get('player_powers') or [])
    return any(p.get('power_id')=='NO_DRAW_POWER' or str(p.get('name') or '').lower()=='no draw' for p in powers)


def choose_plan(state, candidates, width=40, depth=8, triggers=False, retaliation=False, force_first=False):
    cards={c['index']:c for c in state.get('hand',[])}
    enemies={e['index']:e for e in state.get('enemies',[])}
    initial_hp={i:e['hp'] for i,e in enemies.items()}; incoming={i:intent_damage(e) for i,e in enemies.items()}
    hp=state.get('player',{}).get('hp',100)
    start={'self_loss':0,'energy':state.get('energy',0),'block':state.get('player',{}).get('block',0),'hp':dict(initial_hp),'eblock':{i:e.get('block',0) for i,e in enemies.items()},'used':frozenset(),'plan':[],'utility':0.,'strength':0,'vuln':set(),'native_caps':{i:e.get('native_slippery',0) for i,e in enemies.items()},'native_artifacts':{i:e.get('native_artifact',0) for i,e in enemies.items()},'draw_locked':_no_draw_active(state)}
    if triggers:start['triggers']=trigger_rules.initial(state)
    def score(n):
        loss=n['self_loss']+max(0,sum(incoming[i] for i,h in n['hp'].items() if h>0)-n['block']-state.get('player',{}).get('end_turn_block',0))
        kills=sum(h<=0 for h in n['hp'].values());damage=sum(initial_hp[i]-max(0,h) for i,h in n['hp'].items())
        return (damage*.85 + kills*9 + (150 if kills==len(enemies) else 0)
                - loss*1.5 - (10000 if n['self_loss']>=hp else 1000 if loss>=hp else 0) + n['utility'])
    frontier=[start]; best=start;expanded=0
    for _ in range(min(depth,len(cards))):
        children=[]
        for n in frontier:
            if n['self_loss']>=hp:continue
            for c in candidates:
                cmd=c['action'];args=cmd.get('args',cmd)
                if cmd['action']!='play_card':continue
                idx=args['card_index'];card=cards[idx];stats=card.get('stats') or {};cost=max(0,card.get('cost',0))
                if idx in n['used'] or cost>n['energy']:continue
                target=args.get('target_index')
                if target is not None and (target not in n['hp'] or n['hp'][target]<=0):continue
                m=copy.deepcopy(n);m['used']=n['used']|{idx};m['plan']=n['plan']+[c['id']];m['energy']-=cost
                ident=card.get('id','').split('.')[-1]
                block=stats.get('block',0)
                if ident=='ENTRENCH':block=m['block']
                if triggers:
                    if ident=='SECOND_WIND':block=0
                    trigger_rules.gain_block(m,block)
                else:m['block']+=max(0,block)
                previews=card.get('damage_by_target') or []
                for preview in previews:
                    t=preview['target_index']
                    if t not in m['hp'] or m['hp'][t]<=0 or (target is not None and target!=t):continue
                    base=preview.get('native_base_damage',preview.get('damage',0) if retaliation else preview.get('total_damage',preview.get('damage',0))) or 0
                    if ident=='BODY_SLAM':base=m['block']*preview.get('native_target_multiplier',1)
                    base+=m['strength']
                    if t in m['vuln']:base=base*1.5
                    if preview.get('native_slow_count') is not None:base*=1+.1*(preview['native_slow_count']+len(n['used']))
                    base=math.floor(base)
                    for _hit in range(hit_count(card,preview) if retaliation else preview.get('native_hits',1)):
                        if retaliation:
                            if m['hp'][t]<=0 or m['self_loss']>=hp:break
                            if card.get('type')=='Attack':thorns_before_hit(m,enemies[t])
                            if m['self_loss']>=hp:break
                        dealt=max(0,base-m['eblock'][t]);m['eblock'][t]=max(0,m['eblock'][t]-base)
                        if dealt>0 and m['native_caps'].get(t,0)>0:dealt=min(1,dealt);m['native_caps'][t]-=1
                        m['hp'][t]=max(0,m['hp'][t]-dealt)
                if triggers:trigger_rules.after_card(m,card,cards)
                if stats.get('vulnerablepower',0) and target is not None and m['native_artifacts'].get(target,0)>0:
                    m['native_artifacts'][target]-=1
                elif stats.get('vulnerablepower',0) and target is not None:
                    already=any('vulnerab' in str(p.get('name','')).lower() or p.get('power_id')=='VULNERABLE_POWER' for p in enemies[target].get('powers') or [])
                    if not already:m['vuln'].add(target)
                    m['utility']+=stats['vulnerablepower']*1.5
                if stats.get('strengthpower',0):
                    m['strength']+=stats['strengthpower'];m['utility']+=stats['strengthpower']*7
                # Drawn cards are unknown; only the known draw lock is modeled.
                draw=stats.get('cards',0)
                useful_draw=0 if m['draw_locked'] else draw
                m['utility']+=useful_draw*3
                if ident=='BATTLE_TRANCE':m['draw_locked']=True
                if card.get('type')=='Power':
                    m['utility']+=7 + stats.get('energy',0)*12 + stats.get('dexteritypower',0)*8
                else:
                    gain=stats.get('energy',0)
                    if gain>0:m['energy']+=gain;m['utility']+=gain*1.5
                if stats.get('weakpower',0):m['utility']+=min(8,sum(incoming.values())*.25)
                # Unknown non-numeric utility is a small tie breaker, not proof.
                if not previews and not block and not useful_draw and ident!='BATTLE_TRANCE':m['utility']+=.4
                if ident=='ARMAMENTS':m['utility']+=2
                if ident=='BATTLE_TRANCE' and useful_draw:m['utility']+=3
                children.append(m);expanded+=1
                if (force_first and not best['plan']) or score(m)>score(best):best=m
        if not children:break
        # Equivalent plans retain only one abstract endpoint, reducing factorial duplication.
        unique={}
        for n in children:
            key=(n['used'],n['energy'],n['block'],n['self_loss'],tuple(n['hp'].items()),tuple(n['eblock'].items()),n['strength'],tuple(sorted(n['vuln'])),tuple(n['native_caps'].items()),tuple(n['native_artifacts'].items()),n['draw_locked'])
            if triggers:key=key+tuple(n['triggers'].items())
            if key not in unique or score(n)>score(unique[key]):unique[key]=n
        frontier=sorted(unique.values(),key=score,reverse=True)[:width]
    chosen=next((c for c in candidates if best['plan'] and c['id']==best['plan'][0]),next(c for c in candidates if c['action']['action']=='end_turn'))
    return chosen,{'scope':SCOPE,'plan_ids':best['plan'],'score':round(score(best),3),'initial_draw_locked':start['draw_locked'],'predicted_draw_locked':best['draw_locked'],'predicted_self_loss':best['self_loss'],'predicted_total_hp_loss':best['self_loss']+max(0,sum(incoming[i] for i,h in best['hp'].items() if h>0)-best['block']-state.get('player',{}).get('end_turn_block',0)),'predicted_block':best['block'],'predicted_enemy_hp':best['hp'],'expanded':expanded,'width':width,'depth':depth,'trigger_forecast':best.get('triggers')}
