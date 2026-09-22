"""Audit real power increments across captured native end-turn boundaries."""
import gzip,json,hashlib
from pathlib import Path
from rsi.trace import version_manifest
root=Path(__file__).resolve().parents[1];out={'manifest':version_manifest(),'scope':'Factual start-turn power increments, no future-utility or win validation','cases':[],'excluded':[],'sources':{}}
for attempt in [4,5]:
 events=[]
 for report in sorted((root/f'experiments/E013/attempt{attempt}').glob('s*.json')):
  d=json.loads(report.read_text()).get('result',{});p=report.parent/(Path(d.get('trace_path','')).parent.name+'.jsonl.gz')
  if not p.exists():continue
  out['sources'][str(p.relative_to(root))]=hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
  events.extend(json.loads(x)for x in gzip.decompress(p.read_bytes()).decode().splitlines())
 before=None
 for i,r in enumerate(events):
  if r['kind']=='before':before=r['data']['state']
  if r['kind']!='selected' or r['data']['action'].get('action')!='end_turn' or not before:continue
  powers={x['power_id']:x['amount']for x in (before.get('combat')or{}).get('player',{}).get('powers',[])}
  if not any(k in powers for k in ['ROLLING_BOULDER_POWER','DEMON_FORM_POWER']):continue
  after=next((x['data']['state']for x in events[i+1:]if x['kind']=='before'),None)
  tag={'attempt':attempt,'floor':before['run']['floor'],'turn':before['turn']}
  if not after or after.get('screen')!='COMBAT' or after.get('selection') or after['turn']!=before['turn']+1 or after.get('run_id')!=before.get('run_id') or after['run']['floor']!=before['run']['floor']:
   out['excluded'].append({**tag,'reason':'not a direct next-turn combat snapshot'});continue
  newer={x['power_id']:x['amount']for x in after['combat']['player'].get('powers',[])}
  for key in ['ROLLING_BOULDER_POWER','DEMON_FORM_POWER']:
   if key not in powers:continue
   field='ROLLING_BOULDER_POWER'if key=='ROLLING_BOULDER_POWER'else'STRENGTH_POWER';delta=5 if key=='ROLLING_BOULDER_POWER'else powers[key];actual=newer.get(field,0)-powers.get(field,0)
   out['cases'].append({**tag,'power':key,'predicted_delta':delta,'observed_delta':actual,'exact':actual==delta})
out['counts']={'cases':len(out['cases']),'exact':sum(c['exact']for c in out['cases'])};(root/'experiments/E026/audit-v1.json').write_text(json.dumps(out,indent=2)+'\n');print(out['counts']);print([c for c in out['cases']if not c['exact']])
