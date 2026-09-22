"""Compare supported first-action forecasts with later captured settled observations."""
import gzip,json
from pathlib import Path
from rsi.trace import version_manifest
from rsi.live_plan import normalize
from rsi.planner import choose_plan
from rsi.mcp import live_candidates
root=Path(__file__).resolve().parents[1]
indices=list(range(104,108))+list(range(162,208));events=[]
for i in indices:
 report=root/f'experiments/E013/attempt5/s{i:03}.json';d=json.loads(report.read_text())['result'];p=report.parent/(Path(d['trace_path']).parent.name+'.jsonl.gz')
 for row in map(json.loads,gzip.decompress(p.read_bytes()).decode().splitlines()):events.append((i,row))
supported={'STRIKE_IRONCLAD','DEFEND_IRONCLAD','IRON_WAVE','RAGE','FEEL_NO_PAIN','JUGGERNAUT','SECOND_WIND','SHRUG_IT_OFF','POMMEL_STRIKE','BASH'}
cases=[];excluded=[];before=None;selected=None
for pos,(segment,row) in enumerate(events):
 if row['kind']=='before':before=row['data']['state']
 elif row['kind']=='selected':selected=row['data']
 elif row['kind']=='action_result' and before and selected:
  command=selected['action']
  if command['action']!='play_card':continue
  card=next(c for c in before['combat']['hand'] if c['index']==command['card_index'])
  tag={'segment':segment,'card':card['card_id'],'command':command}
  after=next((n['data']['state'] for _,n in events[pos+1:] if n['kind']=='before'),None)
  if card['card_id'] not in supported:excluded.append({**tag,'reason':'outside declared typed support'});continue
  if not after or after.get('screen')!='COMBAT' or after.get('selection') or after.get('turn')!=before.get('turn') or after.get('run',{}).get('floor')!=before['run']['floor']:
   excluded.append({**tag,'reason':'selection/terminal/turn boundary; no comparable next settled observation'});continue
  state=normalize(before);choices=[c for c in live_candidates(before) if c['action']==command or c['action']['action']=='end_turn']
  old,baseline=choose_plan(state,choices,depth=1);new,forecast=choose_plan(state,choices,depth=1,triggers=True)
  if new['action']!=command:excluded.append({**tag,'reason':'planner chose end turn in restricted forecast'});continue
  actual_block=after['combat']['player']['block'];actual_enemies={e['enemy_id']:e['current_hp'] for e in after['combat']['enemies']}
  single=len(state['enemies'])==1
  actual_hp=actual_enemies.get(before['combat']['enemies'][0]['enemy_id'],0) if single else None
  predicted_hp=next(iter(forecast['predicted_enemy_hp'].values())) if single else None
  baseline_hp=next(iter(baseline['predicted_enemy_hp'].values())) if single else None
  cases.append({**tag,'single_target':single,'actual_block':actual_block,'predicted_block':forecast['predicted_block'],'baseline_block':baseline['predicted_block'],'actual_enemy_hp':actual_hp,'predicted_enemy_hp':predicted_hp,'baseline_enemy_hp':baseline_hp,'block_exact':actual_block==forecast['predicted_block'],'hp_exact':actual_hp==predicted_hp if single else None,'random_trigger_damage_unassigned':forecast['trigger_forecast']['uncertain_damage']})
summary={'manifest':version_manifest(),'scope':'offline factual next-observation agreement; no counterfactual battle or win','cases':cases,'excluded':excluded,'counts':{'cases':len(cases),'block_exact':sum(c['block_exact'] for c in cases),'single_target':sum(c['single_target'] for c in cases),'hp_exact':sum(c['hp_exact'] is True for c in cases)},'failures':[c for c in cases if not c['block_exact'] or c['hp_exact'] is False]}
(root/'experiments/E030/native-audit-v1.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['manifest','cases','excluded']}))
