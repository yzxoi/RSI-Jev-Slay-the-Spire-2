"""Native scene candidates from freshly advertised indices only."""
from .mcp import live_candidates
from .trace import digest


def fingerprint(raw):
    combat=dict(raw.get('combat') or {});combat.pop('action_readiness',None)
    keys=['run_id','screen','turn','run','map','selection','reward','event','rest','shop','chest','bundles','capstone','modal','game_over','crystal_sphere']
    return digest({**{k:raw.get(k) for k in keys},'combat':combat})


def candidates(raw, history=None):
    legal=raw.get('available_actions',[]); screen=raw.get('screen');out=[]
    def add(name,item=None,**args):
        if name in legal:out.append({'action':{'action':name,**args},'name':name,'details':item})
    def indexed(name,items,condition=lambda x:True):
        for i,item in enumerate(items or []):
            if condition(item):add(name,item,option_index=item.get('index',i))
    if screen=='COMBAT' and not raw.get('selection'):return live_candidates(raw)
    if raw.get('selection'):
        s=raw['selection']; indexed('select_deck_card',s.get('cards'),lambda c:not c.get('selected'))
        add('confirm_selection',{'selection':s.get('prompt'),'selected_count':s.get('selected_count')})
        if s.get('can_confirm') and s.get('selected_count',0)>=s.get('max_select',1):out=[c for c in out if c['action']['action']=='confirm_selection']
    elif screen=='REWARD':
        s=raw.get('reward') or {}
        if s.get('pending_card_choice'):
            indexed('choose_reward_card',s.get('card_options'));add('skip_reward_cards')
        else:
            skipped=(history or {}).get('skipped_card_reward') == (raw.get('run_id'),(raw.get('run') or {}).get('floor'))
            claimable=[r for r in s.get('rewards',[]) if r.get('claimable') and not (skipped and r.get('reward_type')=='Card')]
            for r in claimable:add('claim_reward',r,option_index=r['index'])
            if not claimable:add('collect_rewards_and_proceed');add('proceed')
            # Receiving gold and opening a card offer do not choose the card.
            if out:out=out[:1]
    elif screen=='MAP':indexed('choose_map_node',(raw.get('map') or {}).get('available_nodes'))
    elif screen=='EVENT':
        indexed('choose_event_option',(raw.get('event') or {}).get('options'),lambda c:not c.get('is_locked') and not c.get('will_kill_player'))
        if not out:add('proceed')
    elif screen=='REST':
        indexed('choose_rest_option',(raw.get('rest') or {}).get('options'),lambda c:c.get('is_enabled'))
        if not out:add('proceed')
    elif screen=='SHOP':
        s=raw.get('shop') or {}
        if 'open_shop_inventory' in legal and not (history or {}).get('shop_closed'):add('open_shop_inventory')
        else:
            for key,cmd in [('cards','buy_card'),('relics','buy_relic'),('potions','buy_potion')]:
                indexed(cmd,s.get(key),lambda c:c.get('is_stocked') and c.get('enough_gold'))
            if (s.get('card_removal') or {}).get('enough_gold'):add('remove_card_at_shop',s['card_removal'])
            add('close_shop_inventory');add('proceed')
    elif screen=='CHEST':
        add('open_chest');indexed('choose_treasure_relic',(raw.get('chest') or {}).get('relic_options'))
        if not out:add('proceed')
    elif screen=='BUNDLE_SELECTION':
        indexed('confirm_bundle',raw.get('bundles'))
        if not out:indexed('choose_bundle',raw.get('bundles'))
    elif screen=='CAPSTONE_SELECTION':
        cap=raw.get('capstone') or {};indexed('choose_capstone_option',cap.get('options') if isinstance(cap,dict) else cap)
    elif screen=='MODAL':add('confirm_modal',raw.get('modal'));add('dismiss_modal',raw.get('modal'))
    elif screen in ['CARD_PILE','CARDS_VIEW','CARD_INSPECT','RELIC_INSPECT']:add('close_cards_view')
    elif screen=='UNLOCK':add('confirm_unlock')
    elif screen=='CRYSTAL_SPHERE':add('proceed')
    else:add('proceed')
    for i,c in enumerate(out):c['id']=f'a{i:03}'
    return out
