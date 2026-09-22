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


def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-run-id',required=True);p.add_argument('--max-actions',type=int,default=2000);p.add_argument('--max-seconds',type=int,default=3600);p.add_argument('--max-usd',type=float,default=3);p.add_argument('--output',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--expert-choice');a=p.parse_args()
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before execution')
    # Cross-worktree lock follows the same local server, not each checkout.
    lockpath=Path('/tmp/rsi-sts2-native-8080.lock')
    with lockpath.open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        uid=str(uuid.uuid4());trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,'config':vars(a),'scope':'native_complete_run'})
        budget=Budget(6000,a.max_usd);jev=Jev(budget) if a.execute else None;start=time.monotonic();raw={};history={};scenes=Counter();last_action=None;repeated=0;waits=0
        result={'run_id':uid,'game_run_id':a.expected_run_id,'status':'error','actions':0,'rejections':0};expert=json.loads(Path(a.expert_choice).read_text()) if a.expert_choice else None
        try:
            mcp=MCP('http://127.0.0.1:8080/mcp',trace);health=mcp.call('health_check')
            if health.get('play_running') or health.get('status')!='ready':raise RuntimeError('Not a healthy single-writer game')
            raw=mcp.call('get_raw_game_state');result['initial_run']=raw.get('run');result['health']=health
            while True:
                if raw.get('run_id')!=a.expected_run_id:raise RuntimeError('Game run identity changed')
                screen=raw.get('screen');scenes[screen]+=1
                if screen=='GAME_OVER':result['status']='victory' if (raw.get('game_over') or {}).get('is_victory') else 'normal_defeat';break
                if result['actions']>=a.max_actions or time.monotonic()-start>a.max_seconds:result['status']='budget_boundary';break
                if screen in ['PAUSE_MENU','SETTINGS']:raise RuntimeError('User paused game')
                cs=candidates(raw,history)
                if not cs:
                    waits+=1
                    if waits>6:raise RuntimeError(f'No supported action: {screen} {raw.get("available_actions")}')
                    mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True});time.sleep(.15);raw=mcp.call('get_raw_game_state');continue
                waits=0;trace.write('before',{'state':raw,'state_hash':fingerprint(raw)});trace.write('candidates',cs)
                if not a.execute:result['status']='read_only_ready';break
                if expert:
                    if expert['state_hash']!=fingerprint(raw):raise RuntimeError('Expert decision does not match current state')
                    selected=next(c for c in cs if c['action']==expert['action']);trace.write('expert_decision',expert);expert=None
                elif len(cs)==1:selected=cs[0]
                else:selected=jev.choose({'state':raw.get('agent_view',raw),'strategy':STRATEGY,'previous_decision':history.get('previous')},cs,trace)[0]
                trace.write('selected',selected)
                if mcp.call('health_check').get('play_running'):raise RuntimeError('Competing autoplay became active')
                fresh=mcp.call('get_raw_game_state')
                if fingerprint(raw)!=fingerprint(fresh) or selected['action'] not in [c['action'] for c in candidates(fresh,history)]:
                    trace.write('stale_proposal_discarded',{'before':fingerprint(raw),'after':fingerprint(fresh)});raw=fresh;continue
                if selected['action']['action']=='end_turn' and (fresh.get('combat') or {}).get('end_turn_will_kill_player'):
                    result['status']='expert_required';trace.write('expert_required',{'reason':'lethal_end_turn','state_hash':fingerprint(fresh)});raw=fresh;break
                signature=(fingerprint(fresh),json.dumps(selected['action'],sort_keys=True));repeated=repeated+1 if signature==last_action else 0
                if repeated>=2:raise RuntimeError('Repeated action without state progress')
                last_action=signature;command={**selected['action'],'raw_state':True,'reason':f"程序摘要：整局策略选择 {selected['name']}；{screen}，楼层 {(raw.get('run') or {}).get('floor')}。"}
                try:answer=mcp.call('act',command)
                except ActionNotAccepted as exc:
                    result['rejections']+=1;trace.write('explicit_rejection',{'error':str(exc),'discarded':selected})
                    if result['rejections']>20:raise
                    mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True});raw=mcp.call('get_raw_game_state');continue
                result['actions']+=1;trace.write('action_result',answer)
                if screen=='MAP':history['shop_closed']=False
                if selected['action']['action']=='close_shop_inventory':history['shop_closed']=True
                if not raw.get('selection'):history['previous']={'screen':screen,'choice':selected}
                mcp.call('wait_until_actionable',{'timeout_seconds':10,'raw_state':True})
                raw=mcp.call('get_raw_game_state');trace.write('after',{'state':raw,'state_hash':fingerprint(raw)})
                print(json.dumps({'step':result['actions'],'action':selected['name'],'screen':raw.get('screen'),'floor':(raw.get('run') or {}).get('floor'),'hp':(raw.get('run') or {}).get('current_hp')},ensure_ascii=False),flush=True)
        except Exception as exc:
            result['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',{'error':result['error']})
        result.update(final_screen=raw.get('screen'),final_run=raw.get('run'),game_over=raw.get('game_over'),scenes=dict(scenes),seconds=round(time.monotonic()-start,3),model_calls=budget.calls,cost_usd=budget.spent,usage_unknown=budget.unknown)
        trace.write('summary',result);result['trace_path']=str(trace.path.relative_to(ROOT));result['trace_sha256']=trace.close();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'manifest':manifest,'result':result},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ['initial_run','final_run','health']},ensure_ascii=False),flush=True)
        if result['status']=='error':raise SystemExit(1)

if __name__=='__main__':main()
