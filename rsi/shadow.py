"""Strict common combat projection for experimental native/headless replay."""
import re

def key(value):return re.sub(r'[^A-Z0-9]','',str(value).split('.')[-1].upper()).removesuffix('POWER')
def powers(items):return sorted((key(p.get('power_id',p.get('name'))),p['amount'])for p in items or [] if p.get('amount'))
def projection(s):
 native='screen'in s
 if native:
  combat=s.get('combat') or {};p=combat.get('player',{});es=[e for e in combat.get('enemies',[])if e.get('is_alive')];hand=combat.get('hand',[])
  return {'decision':'card_select'if s.get('selection')else'combat_play'if s['screen']=='COMBAT'else s['screen'],'round':s.get('turn'),'hp':p.get('current_hp'),'block':p.get('block'),'energy':p.get('energy'),'powers':powers(p.get('powers')),'hand':[(c['card_id'],c['energy_cost'])for c in hand],'enemies':[{'hp':e['current_hp'],'block':e['block'],'powers':powers(e.get('powers')),'incoming':sum(x.get('total_damage')or 0 for x in e.get('intents',[]))}for e in es]}
 p=s.get('player',{});return {'decision':s.get('decision'),'round':s.get('round'),'hp':p.get('hp'),'block':p.get('block'),'energy':s.get('energy'),'powers':powers(s.get('player_powers')),'hand':[(c['id'].split('.')[-1],c['cost'])for c in s.get('hand',[])],'enemies':[{'hp':e['hp'],'block':e['block'],'powers':powers(e.get('powers')),'incoming':sum(x.get('total_damage',x.get('damage',0)*x.get('hits',1))or 0 for x in e.get('intents',[]))}for e in s.get('enemies',[])]}

def command(native):
 a=native['action'];args={k:v for k,v in native.items()if k in ['card_index','target_index']}
 if a=='use_potion':args['potion_index']=native['option_index']
 elif a=='select_deck_card':a='select_cards';args={'indices':str(native['option_index'])}
 elif a not in ['play_card','end_turn']:raise ValueError(f'Unsupported native shadow command: {a}')
 return {'cmd':'action','action':a,'args':args}
