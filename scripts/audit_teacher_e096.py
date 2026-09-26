import json,hashlib
from pathlib import Path
from rsi.trace import digest
from rsi.teacher import terminal
root=Path('.');out=root/'experiments/E096';d=json.loads((out/'result.json').read_text());counts={k:0 for k in ['trace_hash','wire_hash','entry_hash','legal_selected','transition_hash','boundary','no_debug_commands']}
for r in d['results']:
 p=root/r['trace_path'];raw=p.read_bytes();rows=[json.loads(l) for l in raw.splitlines()];wire=p.with_name('wire.jsonl');ws=[json.loads(l) for l in wire.read_bytes().splitlines()]
 counts['trace_hash']+=hashlib.sha256(raw).hexdigest()==r['trace_sha256'];counts['wire_hash']+=hashlib.sha256(wire.read_bytes()).hexdigest()==r['wire_sha256']
 entry=next(x['data'] for x in rows if x['kind']=='entry');counts['entry_hash']+=digest(entry['state'])==r['entry_hash']
 choices=[];trans=[];before=action=None;legal=True;last=entry['state']
 for row in rows:
  k,v=row['kind'],row['data']
  if k=='before':before=v['state_hash']
  elif k=='candidates':choices=v
  elif k=='selected':
   legal&=v in choices;action=v['action']
  elif k=='after':
   assert digest(v['state'])==v['state_hash'];trans.append([before,action,v['state_hash']]);last=v['state']
 counts['legal_selected']+=legal;counts['transition_hash']+=digest(trans)==r['trajectory_sha256'];counts['boundary']+=terminal(last)==r['status'];counts['no_debug_commands']+=all(x['data'].get('cmd') in ('start_run','action') for x in ws if x['kind']=='command')
res={'runs':len(d['results']),'checks_passed':counts,'tested_sha':d['manifest']['code_commit'],'all_passed':all(n==len(d['results']) for n in counts.values()),'scope':'All local raw traces; exact entry, legal fresh selections, accepted trajectory hashes and real Boss boundaries; no debug commands.'}
(out/'audit.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res))
for c in json.loads((out/'fixtures.json').read_text())['cases']:
 rs=[r for r in d['results'] if r['case_id']==c['id']];print(c['id'],[(r['label'],r['status'],r['final_hp']) for r in rs if r['label'] in ('baseline','early_baseline')],len(rs),sum(r['seconds'] for r in rs))
