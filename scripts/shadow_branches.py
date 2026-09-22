"""E005 exact current-prefix branches with bounded baseline rollouts."""
import json,uuid,time,os,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rsi.engine import ROOT,Headless
from rsi.trace import version_manifest,digest
from rsi.shadow import projection
from rsi.policy import combat_candidates
from rsi.potions import with_potions
from rsi.planner import choose_plan
manifest=version_manifest();assert not manifest['tracked_dirty'];os.environ['RSI_RESUME_NATIVE_ROOM']='1';source=json.loads((ROOT/'experiments/E005/prefix-v2.json').read_text());initial=None

def restore(h):
 s=h.send({'cmd':'load_save','path':str(ROOT/'artifacts/private/native-floor7-v2.save')})
 for f in source['frames']:s=h.send(f['command'])
 assert digest(projection(s))==digest(source['final_native_projection'])
 return s

d=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(d)
try:initial=restore(h);choices=with_potions(initial,combat_candidates(initial))
finally:h.close()
assert len(choices)<=10

def branch(c):
 d=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(d);start=time.monotonic();out={'candidate':c,'status':'error','actions':[]}
 try:
  s=restore(h);start_round=s['round'];s=h.send(c['action']);out['actions'].append(c['action']);out['after_first']=projection(s)
  for _ in range(29):
   if s.get('decision')!='combat_play' or s.get('round',start_round)>=start_round+4:break
   selected,plan=choose_plan(s,combat_candidates(s),triggers=True);out['actions'].append(selected['action']);s=h.send(selected['action'])
  out.update(status='computed',end_decision=s.get('decision'),end_hp=s.get('player',{}).get('hp'),end_round=s.get('round'),remaining_enemies=[{'name':e['name'],'hp':e['hp']}for e in s.get('enemies',[])],potions_remaining=[p.get('name')for p in s.get('player',{}).get('potions',[])],combat_won=s.get('decision')in ['card_reward','map_select'],after_first_scope='common projection; macro projections are incomplete')
 except Exception as exc:out['error']=repr(exc)
 finally:h.close()
 out.update(seconds=round(time.monotonic()-start,4),wire_sha256=hashlib.sha256((d/'wire.jsonl').read_bytes()).hexdigest(),wire_path=str((d/'wire.jsonl').relative_to(ROOT)));return out
start=time.monotonic()
with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(branch,choices))
out={'manifest':manifest,'seconds':round(time.monotonic()-start,4),'projection':source['final_native_projection'],'results':results,'scope':'real game engine branches, baseline rollouts limited to30actions/4turns; one development combat, not full-run win evidence'};(ROOT/'experiments/E005/branches-v1.json').write_text(json.dumps(out,indent=2)+'\n')
for r in results:print({k:r.get(k)for k in ['candidate','status','end_hp','end_decision','combat_won','seconds','error']})
