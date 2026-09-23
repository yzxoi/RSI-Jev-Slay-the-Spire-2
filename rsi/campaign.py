"""One-writer native-MCP complete-run controller; normal game actions only."""
import argparse
from collections import Counter
import fcntl
import json
from pathlib import Path
import time
import uuid
from .engine import ROOT
from .full import STRATEGY
from .jev import Budget,Jev
from .mcp import MCP,ActionNotAccepted
from .scenes import candidates,fingerprint
from .trace import Trace,version_manifest
from .live_plan import plan_native
from .encounters import sandpit_rule
from .guard import filter_end_turn
from .status_guard import reserve_toxic_energy
from .settle import settle_turn,turn_key
from .floor_plan import load_floor_plan,plan_context,plan_complete
from .room_plan import load_room_plan,RoomPlanSession,room_context,room_complete
from .event_guard import bound_bridge_reroll


GUIDED_COMBAT_POLICIES={'planned','triggered','retaliate','floor_guided','room_guided'}


def ordinary_candidates(raw, offered, policy, explicit_choice=False):
    if explicit_choice or policy not in GUIDED_COMBAT_POLICIES or raw.get('screen')!='COMBAT' or raw.get('selection'):
        return offered,None
    candidates,report=filter_end_turn(raw,offered)
    candidates,toxic=reserve_toxic_energy(raw,candidates)
    if toxic['excluded']:
        report={**report,'excluded':True,'reason':'reserve_energy_for_toxic','toxic_reservation':toxic}
    return candidates,report


def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-run-id',required=True);p.add_argument('--max-actions',type=int,default=2000);p.add_argument('--max-seconds',type=int,default=3600);p.add_argument('--max-usd',type=float,default=3);p.add_argument('--output',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--expert-choice');p.add_argument('--pause-on-danger',action='store_true');p.add_argument('--danger-hp',type=int,default=20);p.add_argument('--stop-file');p.add_argument('--review-macro',action='store_true');p.add_argument('--review-cards',default='');p.add_argument('--auto-combat-selections',action='store_true');p.add_argument('--floor-plan');p.add_argument('--room-plan');p.add_argument('--combat-policy',choices=['jev','planned','triggered','retaliate','floor_guided','room_guided'],default='planned');a=p.parse_args()
    if (a.combat_policy=='floor_guided') != bool(a.floor_plan):p.error('floor_guided requires --floor-plan, and a floor plan requires floor_guided')
    if (a.combat_policy=='room_guided') != bool(a.room_plan) or (a.room_plan and a.floor_plan):p.error('room_guided requires --room-plan, and plans are mutually exclusive')
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before execution')
    # Cross-worktree lock follows the same local server, not each checkout.
    lockpath=Path('/tmp/rsi-sts2-native-8080.lock')
    with lockpath.open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        uid=str(uuid.uuid4());trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,'config':vars(a),'scope':'native_complete_run'})
        budget=Budget(6000,a.max_usd,conservative_failures=True);jev=Jev(budget) if a.execute else None;start=time.monotonic();raw={};history={};scenes=Counter();last_action=None;repeated=0;waits=0
        result={'run_id':uid,'game_run_id':a.expected_run_id,'status':'error','actions':0,'rejections':0};expert=json.loads(Path(a.expert_choice).read_text()) if a.expert_choice else None
        try:
            mcp=MCP('http://127.0.0.1:8080/mcp',trace);health=mcp.call('health_check')
            if health.get('play_running') or health.get('status')!='ready':raise RuntimeError('Not a healthy single-writer game')
            raw=mcp.call('get_raw_game_state');result['initial_run']=raw.get('run');result['health']=health
            floor_plan=load_floor_plan(a.floor_plan,raw) if a.floor_plan else None
            if floor_plan:trace.write('floor_plan',floor_plan)
            room_plan=load_room_plan(a.room_plan,raw) if a.room_plan else None
            room_session=RoomPlanSession(room_plan) if room_plan else None
            if room_plan:trace.write('room_plan',room_plan)
            settled_key=None
            while True:
                if turn_key(raw) is not None and turn_key(raw)!=settled_key:
                    raw=settle_turn(mcp,raw,trace);settled_key=turn_key(raw)
                if raw.get('run_id')!=a.expected_run_id:raise RuntimeError('Game run identity changed')
                screen=raw.get('screen');scenes[screen]+=1
                if screen=='GAME_OVER':result['status']='victory' if (raw.get('game_over') or {}).get('is_victory') else 'normal_defeat';break
                if plan_complete(floor_plan,raw,result['actions']):result['status']='floor_plan_boundary';break
                if room_complete(room_plan,raw,result['actions']):result['status']='room_plan_boundary';break
                if floor_plan and (raw.get('run') or {}).get('floor',-1)>floor_plan['target_floor']:
                    raise RuntimeError('Floor plan crossed its target boundary')
                if room_plan and (raw.get('run') or {}).get('floor',-1)>room_plan['floor']:
                    raise RuntimeError('Room plan crossed its target boundary')
                if result['actions']>=a.max_actions or time.monotonic()-start>a.max_seconds:result['status']='budget_boundary';break
                if a.stop_file and Path(a.stop_file).exists():result['status']='requested_boundary';break
                if a.pause_on_danger and not expert and screen=='COMBAT' and not raw.get('selection') and (raw.get('combat') or {}).get('player',{}).get('energy',0)>0 and (raw.get('run') or {}).get('current_hp',100)<=a.danger_hp:
                    result['status']='expert_required';trace.write('expert_required',{'reason':'low_hp_before_spending_energy','state_hash':fingerprint(raw)});break
                if screen in ['PAUSE_MENU','SETTINGS']:raise RuntimeError('User paused game')
                cs=candidates(raw,history)
                if not cs:
                    waits+=1
                    if waits>6:raise RuntimeError(f'No supported action: {screen} {raw.get("available_actions")}')
                    mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True});time.sleep(.15);raw=mcp.call('get_raw_game_state');continue
                event_cs,event_guard=bound_bridge_reroll(raw,cs) if not expert else (cs,None)
                if event_guard is not None:trace.write('event_guard',event_guard)
                ordinary_cs,end_turn_guard=ordinary_candidates(raw,event_cs,a.combat_policy,
                    explicit_choice=bool(expert or (room_session and not room_session.applied)))
                if end_turn_guard is not None:trace.write('end_turn_guard',end_turn_guard)
                review_ids=set(a.review_cards.split(','))
                if not expert and screen=='COMBAT' and any(h.get('card_id') in review_ids and h.get('playable') and any(c['action'].get('action')=='play_card' and c['action'].get('card_index')==h['index'] for c in cs) for h in (raw.get('combat') or {}).get('hand',[])):
                    result['status']='expert_required';trace.write('expert_required',{'reason':'explicit_card_review','state_hash':fingerprint(raw)});break
                if a.review_macro and not expert and screen!='COMBAT' and len(cs)>1 and not (a.auto_combat_selections and screen=='CARD_SELECTION' and raw.get('in_combat')):
                    result['status']='expert_required';trace.write('expert_required',{'reason':'macro_review','state_hash':fingerprint(raw)});break
                encounter=sandpit_rule(raw,cs) if screen=='COMBAT' else None
                if encounter:
                    trace.write('encounter_rule',encounter)
                    if encounter['requires_expert'] and not expert:
                        result['status']='expert_required';trace.write('expert_required',{'reason':'sandpit_expiry_before_spending_energy','state_hash':fingerprint(raw)});break
                waits=0;trace.write('before',{'state':raw,'state_hash':fingerprint(raw)});trace.write('candidates',cs)
                if not a.execute:result['status']='read_only_ready';break
                expert_this_action=False;room_opening_this_action=False
                if expert:
                    if expert['state_hash']!=fingerprint(raw):raise RuntimeError('Expert decision does not match current state')
                    selected=next(c for c in cs if c['action']==expert['action']);trace.write('expert_decision',expert);expert_this_action=True;expert=None
                elif room_session and not room_session.applied:
                    selected=room_session.opening(raw,cs)
                    if selected is None:raise RuntimeError('Room opener is no longer legal')
                    trace.write('room_opening_proposed',selected);room_opening_this_action=True
                elif encounter and encounter['selected']:selected=encounter['selected']
                elif len(ordinary_cs)==1:selected=ordinary_cs[0]
                elif a.combat_policy in ['planned','triggered','retaliate','floor_guided','room_guided'] and screen=='COMBAT' and not raw.get('selection'):
                    selected,planning=plan_native(raw,ordinary_cs,triggers=a.combat_policy in ['triggered','retaliate','floor_guided','room_guided'],retaliation=a.combat_policy in ['retaliate','floor_guided','room_guided']);trace.write('planning',planning)
                    if floor_plan or room_plan:
                        selected=jev.choose({'state':raw.get('agent_view',raw),'strategy':STRATEGY,
                                             **plan_context(floor_plan,raw),**room_context(room_plan,raw),
                                             'computed_proposal':planning},ordinary_cs,trace)[0]
                    potions=[c for c in ordinary_cs if c['action']['action']=='use_potion']
                    turnkey=((raw.get('run') or {}).get('floor'),raw.get('turn'))
                    if not floor_plan and not room_plan and potions and history.get('potion_check')!=turnkey:
                        reduced=[selected]+potions
                        for i,c in enumerate(reduced):c={**c,'id':f'p{i:03}'};reduced[i]=c
                        selected=jev.choose({'state':raw.get('agent_view',raw),'strategy':STRATEGY,'question':'Use a potion now to prevent meaningful HP loss or enable a kill, or execute the computed next card. Potions refill; do not hoard at risk of death.','plan':planning},reduced,trace)[0]
                        history['potion_check']=turnkey
                else:selected=jev.choose({'state':raw.get('agent_view',raw),'strategy':STRATEGY,'previous_decision':history.get('previous'),
                                          **plan_context(floor_plan,raw),**room_context(room_plan,raw)},ordinary_cs,trace)[0]
                trace.write('selected',selected)
                if mcp.call('health_check').get('play_running'):raise RuntimeError('Competing autoplay became active')
                fresh=mcp.call('get_raw_game_state')
                if fingerprint(raw)!=fingerprint(fresh) or selected['action'] not in [c['action'] for c in candidates(fresh,history)]:
                    trace.write('stale_proposal_discarded',{'before':fingerprint(raw),'after':fingerprint(fresh)});raw=fresh;continue
                if not expert_this_action and selected['action']['action']=='end_turn' and (fresh.get('combat') or {}).get('end_turn_will_kill_player'):
                    result['status']='expert_required';trace.write('expert_required',{'reason':'lethal_end_turn','state_hash':fingerprint(fresh)});raw=fresh;break
                signature=(fingerprint(fresh),json.dumps(selected['action'],sort_keys=True));repeated=repeated+1 if signature==last_action else 0
                if repeated>=2:raise RuntimeError('Repeated action without state progress')
                last_action=signature;command={**selected['action'],'raw_state':True,'reason':f"程序摘要：整局策略选择 {selected['name']}；{screen}，楼层 {(raw.get('run') or {}).get('floor')}。"}
                try:answer=mcp.call('act',command)
                except ActionNotAccepted as exc:
                    result['rejections']+=1;trace.write('explicit_rejection',{'error':str(exc),'discarded':selected})
                    if room_opening_this_action:raise RuntimeError('Room opener was rejected before execution') from exc
                    if result['rejections']>20:raise
                    mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True});raw=mcp.call('get_raw_game_state');continue
                result['actions']+=1;trace.write('action_result',answer)
                if room_opening_this_action:
                    room_session.accepted();result['astra_opening_actions']=1
                if screen=='MAP':history['shop_closed']=False
                if selected['action']['action']=='skip_reward_cards':history['skipped_card_reward']=(raw.get('run_id'),(raw.get('run') or {}).get('floor'))
                if selected['action']['action']=='close_shop_inventory':history['shop_closed']=True
                if not raw.get('selection'):history['previous']={'screen':screen,'choice':selected}
                mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True})
                raw=mcp.call('get_raw_game_state');trace.write('after',{'state':raw,'state_hash':fingerprint(raw)})
                print(json.dumps({'step':result['actions'],'action':selected['name'],'screen':raw.get('screen'),'floor':(raw.get('run') or {}).get('floor'),'hp':(raw.get('run') or {}).get('current_hp')},ensure_ascii=False),flush=True)
        except Exception as exc:
            result['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',{'error':result['error']})
        result.update(final_screen=raw.get('screen'),final_run=raw.get('run'),game_over=raw.get('game_over'),scenes=dict(scenes),seconds=round(time.monotonic()-start,3),model_calls=budget.calls,cost_usd=budget.spent,usage_unknown=budget.unknown,estimated_usd=budget.estimated_usd,uncertain_calls=budget.uncertain_calls)
        trace.write('summary',result);result['trace_path']=str(trace.path.relative_to(ROOT));result['trace_sha256']=trace.close();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'manifest':manifest,'result':result},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ['initial_run','final_run','health']},ensure_ascii=False),flush=True)
        if result['status']=='error':raise SystemExit(1)

if __name__=='__main__':main()
