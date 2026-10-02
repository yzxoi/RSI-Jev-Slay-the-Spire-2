#!/usr/bin/env python3
"""Offline search accounting and value-vs-simple-HP calibration."""
import argparse,json,statistics,sys
from collections import Counter
from itertools import islice
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.trace import digest
from rsi.checkpoints import wire_pairs,file_hash
from scripts.evaluate_battle_search_e120 import audit,write


def root_diagnostics(records):
 roots=[root for case in records for root in case['roots']]
 accepted=[]
 for case in records:
  decisions=[json.loads(line)['data'] for line in (ROOT/case['trace_path']).read_text().splitlines()
             if json.loads(line)['kind']=='decision']
  # A decision is logged before send. Only the first `steps` have a completed transition.
  accepted.extend(x['search'] for x in decisions[:case['steps']] if 'search'in x)
 med=lambda xs:statistics.median(xs)if xs else None
 return dict(completed_roots=len(roots),executed_roots=len(accepted),
  proposed_changes=sum(r['changed_from_actor']for r in roots),
  executed_changes=sum(r['changed_from_actor']for r in accepted),
  depth_counts=dict(Counter(r['depth']for r in roots)),
  median_legal_actions=med([len(r['edges'])for r in roots]),
  median_visited_actions=med([sum(e['visits']>0 for e in r['edges'])for r in roots]),
  median_max_prior=med([max(e['prior']for e in r['edges'])for r in roots]),
  median_visited_q_spread=med([max(e['q']for e in r['edges']if e['visits'])-
                             min(e['q']for e in r['edges']if e['visits'])for r in roots]))


def completed_pairs(ev,base):
 by_case={x['case']:x for x in base['records']};pairs=[];missing=[]
 for x in ev['records']:
  b=by_case[x['case']]
  if x['status']not in('clear','defeat')or b['status']not in('clear','defeat'):
   missing.append(x['case']);continue
  hp=lambda z:z['hp']if z['status']=='clear'else 0
  pairs.append(dict(case=x['case'],hp_delta=hp(x)-hp(b),status=x['status'],baseline_status=b['status']))
 ds=[p['hp_delta']for p in pairs]
 return dict(scope='Descriptive completed pairs only; not a full-cohort strength estimate',
  n=len(pairs),missing_cases=missing,median_hp_delta=statistics.median(ds)if ds else None,
  improved=sum(d>0 for d in ds),equal=sum(d==0 for d in ds),worse=sum(d<0 for d in ds),pairs=pairs)


def restore_diagnostics(records):
 rows=[]
 for case in records:
  for probe in case['probes']:
   if not probe['entry_verified']:continue
   path=ROOT/probe['trace_path']
   with path.open()as f:manifest=json.loads(next(f))
   with path.with_name('wire.jsonl').open()as f:wire=[json.loads(x)for x in islice(f,3)]
   if len(wire)!=3 or wire[0]['data'].get('type')!='ready' or wire[1]['data'].get('cmd')!='start_run':continue
   ready=wire[0]['time']-manifest['time'];start=wire[2]['time']-wire[1]['time']
   rows.append((ready,start,probe['replay_seconds']-ready-start))
 names=('process_ready','start_run_response','remaining_prefix_and_history')
 return dict(n=len(rows),scope='Approximate stage timing from recorded wall timestamps; restore total uses monotonic clock',
  **{name:dict(total_seconds=sum(x[i]for x in rows),median_seconds=statistics.median(x[i]for x in rows)if rows else None)
     for i,name in enumerate(names)})


def fixture_coverage(path):
 bank=json.loads(Path(path).read_text());splits={}
 for split in ('train','val','test'):
  fixtures=[f for f in bank['fixtures']if f['split']==split]
  if split!='train':
   fixtures=[max((f for f in fixtures if f['seed']==seed),key=lambda f:f['ordinal'])
             for seed in sorted({f['seed']for f in fixtures})]
  splits[split]=dict(entries=len(fixtures),room_types=dict(Counter(f['room_type']for f in fixtures)),
    floor_range=[min(f['floor']for f in fixtures),max(f['floor']for f in fixtures)],
    encounters=dict(Counter(' / '.join(sorted(f['enemies']))for f in fixtures)))
 return dict(source_sha256=file_hash(path),splits=splits,
  scope='Unique natural entry states, not episode counts or all subsequently spawned enemies; train uses all entries, val/test last available')


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
 p.add_argument('--direct');p.add_argument('--fixtures',default=str(ROOT/'experiments/E127/fixtures.json'));a=p.parse_args()
 out=Path(a.output)
 if out.exists():raise ValueError('Preserve analysis')
 r=json.loads(Path(a.source).read_text());models=[]
 direct=json.loads(Path(a.direct).read_text())if a.direct else None
 for row in r['models']:
  arms={}
  for name,ev in row['arms'].items():
   calibration=[];out_of_range=0;leaf_count=0
   for case in ev['records']:
    for probe in case['probes']:
     if not probe.get('leaf_terminal',True) and 'leaf_prediction'in probe:
      leaf_count+=1;out_of_range+=not(-1<=probe['leaf_prediction']<=1.25)
     if 'squared_error'not in probe:continue
     pairs=wire_pairs((ROOT/probe['trace_path']).parent/'wire.jsonl')
     leaf=next(s for _,s in pairs if digest(s)==probe['leaf_hash'])
     hp=leaf['player'];naive=1+.25*hp['hp']/max(1,hp['max_hp'])
     calibration.append({'case':case['case'],'trace_path':probe['trace_path'],'predicted':probe['leaf_prediction'],
                         'actual':probe['return_value'],'naive_clear_current_hp':naive})
   arms[name]={'summary':ev['summary'],'search_summary':ev['search_summary'],'passed':ev['passed'],
               'complete_trajectory_replays':sum(x.get('verification_match',False)for x in ev['records']),
               'root_diagnostics':root_diagnostics(ev['records']),
               'restore_diagnostics':restore_diagnostics(ev['records']),
               'completed_pairs_vs_direct':completed_pairs(ev,direct['arms'][f"L-{row['learner']}"])if direct else None,
               'median_wall_ratio_vs_direct':ev['search_summary']['median_battle_seconds']/statistics.median(
                 x['seconds']for x in direct['arms'][f"L-{row['learner']}"]['records'])if direct else None,
               'nonterminal_leaf_predictions':leaf_count,'out_of_reward_range_predictions':out_of_range,
               'calibration_rows':calibration,
               'terminal_rollout_death_leaves':sum(x['actual']==-1 for x in calibration),
               'positive_predictions_before_rollout_death':sum(x['actual']==-1 and x['predicted']>0 for x in calibration),
               'critic_mse':statistics.mean((x['predicted']-x['actual'])**2 for x in calibration)if calibration else None,
               'assume_clear_current_hp_mse':statistics.mean((x['naive_clear_current_hp']-x['actual'])**2 for x in calibration)if calibration else None}
  models.append({'learner':row['learner'],'arms':arms,'comparisons':row.get('comparisons')})
 result={'source_sha256':file_hash(a.source),'audit':audit(r),'models':models,
         'passed':r['passed'],'strength_gate':r.get('strength_gate'),'value_efficiency_gate':r.get('value_efficiency_gate'),
         'seconds':r['seconds'],'direct_sha256':file_hash(a.direct)if a.direct else None,
         'fixture_coverage':fixture_coverage(a.fixtures),
         'notes':['Calibration is descriptive and conditioned on visited rollout leaves.',
          'The simple comparator assumes a clear at current HP; not an executable policy or win-rate baseline.',
          'Different search paths are not paired counterfactuals; repeated leaves/cases are correlated.',
          'Completed-pair deltas exclude censored cases explicitly and cannot satisfy a full-cohort gate.',
          'Executed root counts require an observed transition, not merely a logged proposed decision.']}
 write(out,result);print(json.dumps({k:v for k,v in result.items()if k not in ('models','notes')},indent=2))
if __name__=='__main__':main()
