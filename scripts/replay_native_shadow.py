"""Two independent loads+frozen commands, with per-step native parity evidence."""
import json,uuid,time,hashlib,os,argparse
from pathlib import Path
from rsi.engine import ROOT,Headless
from rsi.trace import version_manifest,digest
from rsi.shadow import projection
ap=argparse.ArgumentParser();ap.add_argument('--output',default='experiments/E005/replay-v3.json');a=ap.parse_args()
manifest=version_manifest();assert not manifest['tracked_dirty'];os.environ['RSI_RESUME_NATIVE_ROOM']='1';source=json.loads((ROOT/'experiments/E005/prefix-v2.json').read_text());results=[]
for trial in range(2):
 d=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(d);start=time.monotonic();comparisons=[];result={'trial':trial,'status':'error'}
 try:
  s=h.send({'cmd':'load_save','path':str(ROOT/'artifacts/private/native-floor7-v2.save')})
  for i,f in enumerate(source['frames']):
   p=projection(s);expected=f['native_projection'];diff={k:{'native':v,'shadow':p.get(k)}for k,v in expected.items()if digest(v)!=digest(p.get(k))};comparisons.append({'step':i,'equal':not diff,'difference':diff})
   if diff:raise ValueError(f'Parity diverged before accepted command {i}')
   s=h.send(f['command'])
  p=projection(s);expected=source['final_native_projection'];diff={k:{'native':v,'shadow':p.get(k)}for k,v in expected.items()if digest(v)!=digest(p.get(k))};comparisons.append({'step':len(source['frames']),'equal':not diff,'difference':diff});result['status']='current_projection_match'if not diff else'parity_mismatch';result['final_projection']=p
 except Exception as exc:result['error']=repr(exc)
 finally:h.close()
 result.update(seconds=round(time.monotonic()-start,4),comparisons=comparisons,wire_sha256=hashlib.sha256((d/'wire.jsonl').read_bytes()).hexdigest(),wire_path=str((d/'wire.jsonl').relative_to(ROOT)));results.append(result)
report={'manifest':manifest,'results':results,'scope':'frozen observed combat projections only; unexported RNG/pile contents not yet checked'};(ROOT/a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False))
