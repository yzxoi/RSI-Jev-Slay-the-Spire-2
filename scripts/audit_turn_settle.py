"""Replay captured turn-7 partial/complete snapshots without game writes."""
import gzip,json
from pathlib import Path
from rsi.settle import settle_turn
from rsi.trace import version_manifest
root=Path(__file__).resolve().parents[1]
def rows(segment):
 r=json.loads((root/f'experiments/E013/attempt5/{segment}.json').read_text())['result']
 return [json.loads(l) for l in gzip.decompress((root/'experiments/E013/attempt5'/f"{Path(r['trace_path']).parent.name}.jsonl.gz").read_bytes()).decode().splitlines()]
partial=[r['data']['state'] for r in rows('s205') if r['kind']=='after'][-1]
complete=[r['data']['state'] for r in rows('s206') if r['kind']=='before'][0]
class Replay:
 def __init__(self):self.now=0.;self.events=[];self.calls=[]
 def clock(self):return self.now
 def sleep(self,n):self.now+=n
 def write(self,k,d):self.events.append({'kind':k,'data':d})
 def call(self,name):
  self.calls.append(name)
  return complete if self.now>=.45 else partial
r=Replay();out=settle_turn(r,partial,r,clock=r.clock,sleep=r.sleep)
assert out==complete and len(out['combat']['hand'])==5
report={'manifest':version_manifest(),'scope':'offline captured state replay with synthetic observation timing, not live strength','sources':['E013 attempt5 s205 after','E013 attempt5 s206 before'],'partial_hand':len(partial['combat']['hand']),'complete_hand':len(out['combat']['hand']),'seconds':r.now,'read_only_calls':r.calls,'events':r.events,'result':'passed'}
(root/'experiments/E027/captured-replay-v1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['manifest','events','read_only_calls']}))
