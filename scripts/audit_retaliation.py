"""Factual E030 floor22 first-action audit; never counterfactual wins."""
import gzip,json
from pathlib import Path
from rsi.trace import version_manifest
from rsi.live_plan import normalize
from rsi.planner import choose_plan
from rsi.mcp import live_candidates
root=Path(__file__).resolve().parents[1];p=root/'experiments/E038/source-native/0dc40c29-ec38-40ba-8bef-b9df0a6887f4.jsonl.gz';rows=[json.loads(l) for l in gzip.decompress(p.read_bytes()).decode().splitlines()];cases=[];excluded=[];before=None
for i,r in enumerate(rows):
 if r['kind']=='before':before=r['data']['state']
 if r['kind']!='selected' or not before or before.get('run',{}).get('floor')!=22:continue
 cmd=r['data']['action']
 if cmd['action']!='play_card':continue
 card=next(c for c in before['combat']['hand'] if c['index']==cmd['card_index'])
 if card.get('card_type')!='Attack' and card['card_id'] not in {'STRIKE_IRONCLAD','ANGER','SWORD_BOOMERANG','HEADBUTT'}:continue
 after=next((x['data']['state'] for x in rows[i+1:] if x['kind']=='before'),None)
 if after is None:after=next((x['data']['state'] for x in rows[i+1:] if x['kind']=='after'),None)
 tag={'seq':r['seq'],'turn':before['turn'],'card':card['card_id']}
 if not after or after.get('selection') or after['screen']!='COMBAT' or after['turn']!=before['turn']:
  excluded.append({**tag,'reason':'no comparable same-turn observation'});continue
 cs=[c for c in live_candidates(before) if c['action']==cmd or c['action']['action']=='end_turn'];state=normalize(before)
 _,old=choose_plan(state,cs,depth=1,triggers=True,force_first=True);_,new=choose_plan(state,cs,depth=1,triggers=True,retaliation=True,force_first=True)
 actual={'block':after['combat']['player']['block'],'self_loss':before['combat']['player']['current_hp']-after['combat']['player']['current_hp']}
 expected={'block':new['predicted_block'],'self_loss':new['predicted_self_loss']}
 cases.append({**tag,'actual':actual,'predicted':expected,'baseline':{'block':old['predicted_block'],'self_loss':old['predicted_self_loss']},'exact':actual==expected})
out={'manifest':version_manifest(),'source':str(p.relative_to(root)),'scope':'factual own HP/block after each observed attack; no claim about counterfactual decisions/wins','cases':cases,'excluded':excluded,'counts':{'cases':len(cases),'exact':sum(c['exact'] for c in cases),'baseline_exact':sum(c['actual']==c['baseline'] for c in cases)}}
(root/'experiments/E038/native-audit-v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['counts']));print([c for c in cases if not c['exact']])
