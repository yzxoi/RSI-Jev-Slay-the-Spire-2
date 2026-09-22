"""Compare two adapters on preserved, observed single-card transitions."""
import argparse,collections,hashlib,json,pathlib,subprocess,sys,types
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from rsi.live_plan import normalize
from rsi.trace import version_manifest
p=argparse.ArgumentParser();p.add_argument('--trace-root',required=True);p.add_argument('--old-ref',default='eea1b87^');p.add_argument('--output',required=True);args=p.parse_args()
old=types.ModuleType('rsi.oldliveplan');old.__package__='rsi';exec(subprocess.check_output(['git','show',args.old_ref+':rsi/live_plan.py'],text=True),old.__dict__)
rows=[];sources=[]
for path in pathlib.Path(args.trace_root).glob('*/decisions.jsonl'):
 before=None;selected=None
 for line in path.read_text().splitlines():
  r=json.loads(line)
  if r['kind']=='before':before=r['data'].get('state');selected=None
  elif r['kind']=='selected':selected=r['data']
  elif r['kind']=='after' and before and selected:
   after=r['data'].get('state');cmd=selected.get('action',{})
   if cmd.get('action')!='play_card' or not after or not before.get('combat') or not after.get('combat') or before.get('turn')!=after.get('turn'):continue
   card=next(c for c in before['combat']['hand'] if c['index']==cmd['card_index']);idx=card['index'];target=cmd.get('target_index');record={'trace':path.parent.name,'seq':r['seq'],'card':card['card_id'],'block_actual':after['combat']['player']['block']-before['combat']['player']['block']}
   try:
    norms={label:fn(before) for label,fn in [('old',old.normalize),('new',normalize)]}
   except (TypeError,KeyError):continue
   for label,s in norms.items():
    c=next(c for c in s['hand'] if c['index']==idx);record[label+'_block']=(c.get('stats') or {}).get('block',0)
    if target is not None:
     be=next((e for e in before['combat']['enemies'] if e['index']==target),None);ae=next((e for e in after['combat']['enemies'] if e['index']==target),None)
     if be and ae and len(before['combat']['enemies'])==len(after['combat']['enemies']) and be.get('enemy_id')==ae.get('enemy_id') and be.get('max_hp')==ae.get('max_hp'):
      damage=next((x.get('total_damage',x.get('damage',0)) for x in c['damage_by_target'] if x['target_index']==target),0);record[label+'_damage']=min(be['current_hp'],max(0,damage-be['block']));record['damage_actual']=be['current_hp']-ae['current_hp']
   rows.append(record)
 if any(r['trace']==path.parent.name for r in rows):sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
summary={}
for metric in ['block','damage']:
 subset=[r for r in rows if metric+'_actual' in r]
 summary[metric]={'n':len(subset),**{label:{'exact':sum(r[label+'_'+metric]==r[metric+'_actual'] for r in subset),'absolute_error':sum(abs(r[label+'_'+metric]-r[metric+'_actual']) for r in subset)} for label in ['old','new']}}
out={'manifest':version_manifest(),'old_ref':args.old_ref,'summary':summary,'sources':sources,'observations':rows,'scope':'Observed immediate transitions only; omitted terminal transitions, no counterfactual strength inference. Unknown triggers and rounded previews may mismatch.'};pathlib.Path(args.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(summary))
