"""Replay exact failed engine wire prefixes; no model choices or game edits."""
import argparse,json,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rsi.engine import Headless,ROOT,first_action
from rsi.trace import version_manifest
p=argparse.ArgumentParser();p.add_argument('--wire',required=True);p.add_argument('--output',required=True);a=p.parse_args()
m=version_manifest();assert not m['tracked_dirty']
rows=[json.loads(l) for l in Path(a.wire).read_text().splitlines()];commands=[r['data'] for r in rows if r['kind']=='command'];d=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(d);out={'manifest':m,'source_wire':a.wire,'command_count':len(commands),'wire_path':str(d/'wire.jsonl'),'status':'error'}
try:
 for i,c in enumerate(commands):
  before=locals().get('s');s=h.send(c)
  out['replayed']=i+1
  if i==len(commands)-1:out.update(last_command=c,before=before,after=s)
 out['status']='prefix_passed';start_round=s.get('round');extra=[]
 for _ in range(30):
  if s.get('decision')!='combat_play' or s.get('round')!=start_round:break
  cmd=first_action(s);s=h.send(cmd);extra.append({'command':cmd,'decision':s.get('decision'),'round':s.get('round')})
 out.update(extra=extra,final=s)
except Exception as e:out['error']=str(e)
finally:h.close()
Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['manifest','before','after','final']},ensure_ascii=False))
