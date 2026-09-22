"""Typed arithmetic for observed block/exhaust chains, with random targets explicit."""
import re

def key(o):
    value=o.get('power_id',o.get('relic_id',o.get('id',o.get('name',''))))
    return re.sub(r'[^A-Z0-9]+','_',str(value).split('.')[-1].upper()).strip('_').removesuffix('_POWER')

def initial(state):
    powers={key(p):p.get('amount',0) for p in (state.get('player_powers') or state.get('player',{}).get('powers') or [])}
    relics={key(r) for r in state.get('player',{}).get('relics',[]) or [] if not r.get('is_melted')}
    return {'fnp':powers.get('FEEL_NO_PAIN',0),'juggernaut':powers.get('JUGGERNAUT',0),'rage':powers.get('RAGE',0),
            'daughter':int('DAUGHTER_OF_THE_WIND' in relics),'soul':int('FORGOTTEN_SOUL' in relics),'uncertain_damage':0}

def power_damage(node, amount):
    alive=[i for i,hp in node['hp'].items() if hp>0]
    if len(alive)>1:
        node['triggers']['uncertain_damage']+=amount
        return  # Never assign random damage to a convenient target or claim a kill.
    if not alive:return
    i=alive[0];absorbed=min(node['eblock'][i],amount);node['eblock'][i]-=absorbed
    node['hp'][i]=max(0,node['hp'][i]-amount+absorbed)

def gain_block(node, amount):
    amount=max(0,amount)
    node['block']+=amount
    if amount and node['triggers']['juggernaut']:power_damage(node,node['triggers']['juggernaut'])

def install(node, ident, stats):
    if ident=='FEEL_NO_PAIN':node['triggers']['fnp']+=stats.get('power',stats.get('feelnopainpower',0))
    elif ident=='JUGGERNAUT':node['triggers']['juggernaut']+=stats.get('juggernautpower',0)
    elif ident=='RAGE':node['triggers']['rage']+=stats.get('power',stats.get('ragepower',0))

def exhaust(node):
    if node['triggers']['fnp']:gain_block(node,node['triggers']['fnp'])
    if node['triggers']['soul']:power_damage(node,node['triggers']['soul'])

def after_card(node, card, cards):
    ident=card['id'].split('.')[-1];stats=card.get('stats') or {};kind=card.get('type')
    install(node,ident,stats)
    if kind=='Attack':
        if node['triggers']['daughter']:gain_block(node,node['triggers']['daughter'])
        if node['triggers']['rage']:gain_block(node,node['triggers']['rage'])
    if ident=='SECOND_WIND':
        consumed=[c for i,c in cards.items() if i not in node['used'] and c.get('type')!='Attack']
        for c in consumed:
            node['used']=node['used']|{c['index']};exhaust(node);gain_block(node,stats.get('block',0))
    # Native export omits keyword lists; these IDs were observed exhausting in E013.
    if 'Exhaust' in (card.get('keywords') or []) or ident in {'OFFERING','DARK_SHACKLES','FORGOTTEN_RITUAL'}:exhaust(node)
