"""Freeze accepted native writes, excluding selected but stale/rejected proposals."""
import argparse,json
from pathlib import Path
from rsi.shadow import projection,command
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);a=ap.parse_args();frames=[]
for report in ['native-v3.json','native-v4-astra2.json','native-v5.json']:
 d=json.loads((a.source_root/'experiments/E038'/report).read_text())['result'];before=None;selected=None
 for row in map(json.loads,(a.source_root/d['trace_path']).read_text().splitlines()):
  if row['kind']=='before':before=row['data']['state'];selected=None
  if row['kind']=='selected':selected=row['data']
  if row['kind']=='action_result'and before and selected and before.get('run',{}).get('floor')==7:
   frames.append({'native_projection':projection(before),'command':command(selected['action']),'source_trace_sha256':d['trace_sha256'],'seq':row['seq']})
out={'frames':frames,'final_native_projection':projection(json.loads(Path('artifacts/private/native-floor7-state.json').read_text()))};Path('experiments/E005/prefix-v2.json').write_text(json.dumps(out,indent=2)+'\n');print('accepted commands',len(frames))
