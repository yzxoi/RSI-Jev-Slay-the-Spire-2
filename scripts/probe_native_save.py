"""Read-only native capture plus isolated save loads; fail closed on parity."""
import json,uuid,time,hashlib
from pathlib import Path
from rsi.engine import Headless,ROOT
from rsi.trace import Trace,version_manifest
from rsi.mcp import MCP
manifest=version_manifest();assert not manifest['tracked_dirty'];t=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'E005 readonly native parity capture'})
m=MCP('http://127.0.0.1:8080/mcp',t);native=m.call('get_raw_game_state');assert native['run_id']=='EFUZ4NHFCXBT' and native['run']['floor']==7
(ROOT/'artifacts/private/native-floor7-state.json').write_text(json.dumps(native));native_sha=t.close()
report={'manifest':manifest,'scope':'two isolated copies; no game mutations','native_trace_sha256':native_sha,'loads':[]}
for iteration in range(2):
 directory=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(directory);start=time.monotonic()
 try:
  state=h.send({'cmd':'load_save','path':str(ROOT/'artifacts/private/native-floor7.save'),'lang':'en'})
  (ROOT/f'artifacts/private/loaded-{iteration}.json').write_text(json.dumps(state))
  report['loads'].append({'seconds':round(time.monotonic()-start,4),'state_sha256':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest(),'decision':state.get('decision'),'context':state.get('context'),'hp':state.get('player',{}).get('hp'),'hand':[c['id'] for c in state.get('hand',[])],'enemies':[{k:e.get(k)for k in ['name','hp','block']}for e in state.get('enemies',[])],'error':state.get('message'),'wire_path':str(directory.relative_to(ROOT)/'wire.jsonl')})
 except Exception as exc:report['loads'].append({'error':repr(exc),'seconds':round(time.monotonic()-start,4)})
 finally:h.close()
report['repeat_load_equal']=len(report['loads'])==2 and report['loads'][0].get('state_sha256')==report['loads'][1].get('state_sha256') and report['loads'][0].get('state_sha256') is not None
(ROOT/'experiments/E005/load-v1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='manifest'},ensure_ascii=False))
