"""Replay the frozen Tools of the Trade boundary, resolving its real prompt."""
import json,gzip,uuid,hashlib
from pathlib import Path
from rsi.engine import ROOT,Headless,first_action
from rsi.trace import version_manifest
manifest=version_manifest();assert not manifest['tracked_dirty']
source=ROOT/'experiments/E036/tools-trade-prefix.jsonl.gz';rows=[json.loads(l) for l in gzip.decompress(source.read_bytes()).decode().splitlines()];commands=[r['data'] for r in rows if r['kind']=='command']
d=ROOT/'artifacts/runs'/str(uuid.uuid4());h=Headless(d);report={'manifest':manifest,'scope':'exact wire replay; no model or game-value edits','commands':len(commands),'status':'error'}
try:
 for cmd in commands:s=h.send(cmd)
 report['pending']=s;assert s['decision']=='card_select' and len(s['cards'])==6
 hp=s['player']['hp'];selection=first_action(s);report['selection']=selection;s=h.send(selection);report['after']=s
 assert s['decision']=='combat_play' and s['round']==3 and s['player']['hp']==hp
 report['status']='passed'
except Exception as exc:report['error']=repr(exc)
finally:h.close()
wire=(d/'wire.jsonl').read_bytes();report['wire_sha256']=hashlib.sha256(wire).hexdigest();report['engine_log_tail']=(d/'engine.stderr.log').read_text()[-1800:]
assert 'forcing game_over' not in report['engine_log_tail']
(ROOT/'experiments/E036/tools-trade-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(ROOT/'experiments/E036/tools-trade-v1-wire.jsonl.gz').write_bytes(gzip.compress(wire,mtime=0));print({k:v for k,v in report.items() if k not in ['manifest','pending','after','engine_log_tail']})
