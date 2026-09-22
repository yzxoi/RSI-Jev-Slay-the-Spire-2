"""Bounded E005 Jev selection of audited engine plans, one native writer."""
import json,uuid,time,fcntl,gzip
from pathlib import Path
from rsi.engine import ROOT
from rsi.mcp import MCP
from rsi.trace import Trace,version_manifest,digest
from rsi.shadow import projection
from rsi.scenes import candidates,fingerprint
from rsi.jev import Budget,Jev
from rsi.settle import settle_turn
manifest=version_manifest();assert not manifest['tracked_dirty'];lock=open('/tmp/rsi-sts2-native-8080.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
t=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'E005 two-action native shadow demo; no Astra strategic choice'});m=MCP('http://127.0.0.1:8080/mcp',t);budget=Budget(10,.05,conservative_failures=True);jev=Jev(budget);report={'status':'error','actions':0};data=json.loads((ROOT/'experiments/E005/branches-v1.json').read_text());t.write('shadow_source',{'code_commit':data['manifest']['code_commit'],'report_sha256':__import__('hashlib').sha256((ROOT/'experiments/E005/branches-v1.json').read_bytes()).hexdigest()})
def native_cmd(cmd):
 out={'action':cmd['action'],**cmd.get('args',{})}
 if 'potion_index'in out:out['option_index']=out.pop('potion_index')
 return out
try:
 s=settle_turn(m,m.call('get_raw_game_state'),t);assert s['run_id']=='EFUZ4NHFCXBT';assert digest(projection(s))==digest(data['projection'])
 legal=[c['action']for c in candidates(s,{})];choices=[]
 for i,r in enumerate(data['results']):
  if r['status']!='computed' or native_cmd(r['candidate']['action'])not in legal:continue
  choices.append({'id':f'b{i:03}','action':native_cmd(r['candidate']['action']),'name':r['candidate']['name'],'forecast':{k:r.get(k)for k in ['end_hp','end_decision','end_round','combat_won','potions_remaining','remaining_enemies']},'planned_actions':len(r['actions']),'uses_potion':r['candidate']['action']['action']=='use_potion','branch_index':i})
 selected,_=jev.choose({'state':projection(s),'question':'Choose a computed plan. Prioritize winning combat with maximum remaining HP. When wins/HP tie, conserve potions and prefer fewer turns/actions. These engine rollouts reproduce this exact current state but are bounded baseline plans, not proof of optimality. Reward potions are auto-granted by the CLI and have not yet been claimed natively.'},choices,t);branch=data['results'][selected['branch_index']];report['jev_choice']=selected;t.write('selected_plan',selected)
 for i,cmd in enumerate(branch['actions'][:2]):
  fresh=m.call('get_raw_game_state');assert fresh['run_id']=='EFUZ4NHFCXBT' and fingerprint(fresh)==fingerprint(s),'State changed before write'
  action=native_cmd(cmd);assert action in [c['action']for c in candidates(fresh,{})]
  t.write('before',{'state':fresh});t.write('selected',{'action':action,'source':'Jev-selected-engine-plan'});answer=m.call('act',{**action,'raw_state':True,'reason':'Jev选择了引擎试算线路；逐步核对真实局面，只执行本次演示的最多2步。'});report['actions']+=1;t.write('action_result',answer)
  deadline=time.monotonic()+8
  while True:
   m.call('wait_until_actionable',{'timeout_seconds':2,'raw_state':True});s=m.call('get_raw_game_state')
   matched=(digest(projection(s))==digest(branch['after_first']))if i==0 else (s['screen']=='REWARD'and s['run']['current_hp']==branch['end_hp'])
   if matched:break
   if time.monotonic()>deadline:raise RuntimeError('Native transition did not match shadow prediction')
   time.sleep(.15)
  t.write('after',{'state':s,'matches_shadow':matched})
 report.update(status='passed',final_screen=s['screen'],hp=s['run']['current_hp'],floor=s['run']['floor'],game_run_id=s['run_id'])
except Exception as exc:report['error']=repr(exc)
report.update(model_calls=budget.calls,cost_usd=budget.spent,trace_path=str(t.path.relative_to(ROOT)));t.write('summary',report);report['trace_sha256']=t.close();(ROOT/'experiments/E005/native-demo-v1.json').write_text(json.dumps({'manifest':manifest,'result':report},indent=2)+'\n');(ROOT/f'experiments/E005/{t.directory.name}.jsonl.gz').write_bytes(gzip.compress(t.path.read_bytes(),mtime=0));print(json.dumps(report,ensure_ascii=False))
