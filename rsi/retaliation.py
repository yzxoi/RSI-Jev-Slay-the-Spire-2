"""Blockable Thorns before powered attack hits; no fabricated random allocation."""
from .triggers import key

def thorns_before_hit(node, enemy):
    damage=sum(max(0,p.get('amount',0)) for p in enemy.get('powers') or [] if key(p)=='THORNS')
    absorbed=min(node['block'],damage)
    node['block']-=absorbed
    node['self_loss']+=damage-absorbed

def hit_count(card, preview):
    if 'native_hits' in preview:return max(1,int(preview['native_hits']))
    if 'repeat' in preview:return max(1,int(preview['repeat']))
    return 2 if card.get('id','').split('.')[-1]=='TWIN_STRIKE' else 1
