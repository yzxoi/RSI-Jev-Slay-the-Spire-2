"""Potion candidates use engine-exported slots and real action commands."""
from .engine import action

def with_potions(state,choices):
    out=list(choices)
    for potion in state.get('player',{}).get('potions',[]):
        if potion.get('can_use') is False or potion.get('usage') in ('Automatic', 'None'):
            continue
        kind=potion.get('target_type')
        if kind=='AnyEnemy':targets=[e['index'] for e in state.get('enemies',[])]
        elif kind in ['Self','AnyPlayer','AllEnemies','RandomEnemy','None','TargetedNoCreature']:targets=[None]
        else:continue
        for target in targets:
            args={'potion_index':potion['index']}
            if target is not None:args['target_index']=target
            out.append({'id':f'p{len(out):03}','action':action('use_potion',**args),'name':potion['name'],'details':potion})
    return out
