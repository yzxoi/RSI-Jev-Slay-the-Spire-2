"""Audited expert choice followed by bounded automatic native play."""
import argparse,json,pathlib,subprocess,sys,time,uuid
from .mcp import MCP
from .trace import Trace,version_manifest
from .engine import ROOT
from .scenes import fingerprint,candidates
from .settle import settle_turn

def compact(s):
 r=s.get('run') or {};c=s.get('combat') or {}
 out={'run_id':s.get('run_id'),'screen':s.get('screen'),'floor':r.get('floor'),'hp':r.get('current_hp'),'max_hp':r.get('max_hp'),'gold':r.get('gold'),'turn':s.get('turn')}
 if c:
  out['player']=c.get('player');out['hand']=[{k:h.get(k) for k in ['index','card_id','name','energy_cost','playable','resolved_rules_text']} for h in c.get('hand',[])];out['enemies']=c.get('enemies');out['potions']=[p for p in r.get('potions',[]) if p.get('occupied')]
 for key in ['event','rest','reward','selection','shop','map','bundles','capstone','game_over','crystal_sphere']:
  if s.get(key):out[key]=s[key]
 out['choices']=candidates(s,{}) if s.get('screen')!='GAME_OVER' else []
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--action');p.add_argument('--reason');p.add_argument('--output');p.add_argument('--max-actions',type=int,default=2000);p.add_argument('--review-cards',default='');p.add_argument('--auto-combat-selections',action='store_true');p.add_argument('--danger-hp',type=int,default=35);p.add_argument('--combat-policy',choices=['planned','jev','triggered'],default='planned');a=p.parse_args();manifest=version_manifest()
 if manifest['tracked_dirty']:raise RuntimeError('Commit before execution')
 t=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'pilot_boundary_observation'});m=MCP('http://127.0.0.1:8080/mcp',t);s=m.call('get_raw_game_state');assert s['run_id']==a.run_id;s=settle_turn(m,s,t)
 if a.action:
  for _ in range(6):
   if candidates(s,{}) or s.get('screen')!='COMBAT':break
   m.call('wait_until_actionable',{'timeout_seconds':5,'raw_state':True});time.sleep(.15);s=m.call('get_raw_game_state');assert s['run_id']==a.run_id;s=settle_turn(m,s,t)
  cmd=json.loads(a.action);assert cmd in [c['action'] for c in candidates(s,{})];assert a.output and a.reason
  d=ROOT/'artifacts/private';d.mkdir(exist_ok=True);expert=d/(str(uuid.uuid4())+'.json');expert.write_text(json.dumps({'state_hash':fingerprint(s),'action':cmd,'source':'Astra','reason':a.reason},ensure_ascii=False));t.write('expert_handoff',{'path':str(expert),'choice':cmd,'reason':a.reason});t.close()
  with (d/(pathlib.Path(a.output).stem+'.log')).open('w') as log:
   subprocess.run([sys.executable,'-m','rsi.campaign','--expected-run-id',a.run_id,'--execute','--combat-policy',a.combat_policy,'--expert-choice',str(expert),'--max-actions',str(a.max_actions),'--review-cards',a.review_cards,'--review-macro','--pause-on-danger','--danger-hp',str(a.danger_hp),'--stop-file','/tmp/rsi-sts2-native.pause','--output',a.output]+(['--auto-combat-selections'] if a.auto_combat_selections else []),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  t=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'pilot_result_observation'});m=MCP('http://127.0.0.1:8080/mcp',t);s=m.call('get_raw_game_state');print('RESULT',json.dumps({k:v for k,v in json.loads(pathlib.Path(a.output).read_text())['result'].items() if k not in ['initial_run','final_run','health']},ensure_ascii=False))
 print(json.dumps(compact(s),ensure_ascii=False));t.close()
if __name__=='__main__':main()
