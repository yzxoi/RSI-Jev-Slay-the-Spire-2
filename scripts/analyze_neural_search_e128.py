#!/usr/bin/env python3
"""Offline search accounting and value-vs-simple-HP calibration."""
import argparse,json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.trace import digest
from rsi.checkpoints import wire_pairs,file_hash
from scripts.evaluate_battle_search_e120 import audit,write


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 out=Path(a.output)
 if out.exists():raise ValueError('Preserve analysis')
 r=json.loads(Path(a.source).read_text());models=[]
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
               'nonterminal_leaf_predictions':leaf_count,'out_of_reward_range_predictions':out_of_range,
               'calibration_rows':calibration,
               'critic_mse':statistics.mean((x['predicted']-x['actual'])**2 for x in calibration)if calibration else None,
               'assume_clear_current_hp_mse':statistics.mean((x['naive_clear_current_hp']-x['actual'])**2 for x in calibration)if calibration else None}
  models.append({'learner':row['learner'],'arms':arms,'comparisons':row.get('comparisons')})
 result={'source_sha256':file_hash(a.source),'audit':audit(r),'models':models,
         'passed':r['passed'],'strength_gate':r.get('strength_gate'),'value_efficiency_gate':r.get('value_efficiency_gate'),
         'seconds':r['seconds'],'notes':['Calibration is descriptive and conditioned on visited rollout leaves.',
          'The simple comparator assumes a clear at current HP; not an executable policy or win-rate baseline.',
          'Different search paths are not paired counterfactuals; repeated leaves/cases are correlated.']}
 write(out,result);print(json.dumps({k:v for k,v in result.items()if k not in ('models','notes')},indent=2))
if __name__=='__main__':main()
