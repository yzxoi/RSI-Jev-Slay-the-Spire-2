"""Explicit delayed effects; forecast values are assumptions, not current damage."""
HORIZON=3
DISCOUNT=.8

def forecast(card):
    ident=card.get('id',card.get('card_id','')).split('.')[-1];st=card.get('stats') or {};turns=[]
    for turn in range(1,HORIZON+1):
        if ident=='ROLLING_BOULDER':turns.append({'turn':turn,'unpowered_damage_each':st.get('rollingboulderpower',st.get('power',5))+(turn-1)*st.get('incrementamount',5),'strength':0})
        elif ident=='DEMON_FORM':turns.append({'turn':turn,'unpowered_damage_each':0,'strength':turn*st.get('strengthpower',0)})
    return {'card':ident,'current_damage':0,'current_strength':0,'turns':turns,'assumptions':{'future_turns':HORIZON,'discount':DISCOUNT,'future_attacks_per_turn':1,'future_enemy_block':0,'unknown_future_mechanics':True}}

def value(future, enemy_hp):
    alive=[hp for hp in enemy_hp.values() if hp>0]
    if not alive:return 0
    # Bounded optimistic future value; never modifies current enemy HP or kills.
    damage=sum(DISCOUNT**row['turn']*(row['unpowered_damage_each']*len(alive)+row['strength'])for item in future for row in item['turns'])
    return min(sum(alive),damage)*.85
