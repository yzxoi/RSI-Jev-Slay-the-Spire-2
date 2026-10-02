#!/usr/bin/env python3
"""Compact E127 accounting and held-out value diagnostics; no refitting."""
import argparse,json,statistics
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import audit,write
from scripts.analyze_ppo_e125 import behaviors


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
 if out.exists():raise ValueError('Preserve prior analysis')
 paths={k:ROOT/'artifacts/runs'/f'e127-{k}-v1.json'for k in ('fixtures','preflight','training','test')}
 reports={k:json.loads(p.read_text())for k,p in paths.items()};t=reports['training'];test=reports['test']
 models=[]
 for r in t['learners']:
  for cp in r['checkpoints']:
   if file_hash(ROOT/cp['path'])!=cp['sha256']:raise ValueError('Checkpoint changed')
  us=r['updates'];ev=test['arms'][f"{r['size']}-{r['learner']}"]
  calibration=[x['value_calibration']for x in ev['records']if 'value_calibration'in x]
  models.append({**{k:r[k]for k in ('size','learner','status','parameters','selected','seconds','work_seconds')},
   'episodes':sum(len(u['episodes'])for u in us),'transitions':sum(u['summary']['steps']for u in us),
   'optimizer_seconds':sum(u.get('optimization_seconds',0)for u in us),
   'validation_curve':[{k:v[k]for k in ('update','passed','summary')}for v in r['validations']],
   'test':ev['summary'],'behavior':behaviors(ev['records']),
   'heldout_greedy_mc_value_mse':sum(x['n']*x['mse']for x in calibration)/sum(x['n']for x in calibration)if calibration else None})
 result={'sources':{k:{'path':str(p.relative_to(ROOT)),'sha256':file_hash(p)}for k,p in paths.items()},
         'audit':audit(reports),'models':models,'comparisons':test['comparisons'],
         'total_training_episodes':sum(m['episodes']for m in models),'total_training_transitions':sum(m['transitions']for m in models),
         'training_wall_seconds':sum(m['seconds']for m in models),'optimizer_seconds':sum(m['optimizer_seconds']for m in models),
         'heldout_seeds':24,'scale_gate':test['scale_gate'],'capacity_gate':test['capacity_gate'],
         'selected_policy_replays':sum(r.get('verification_match',False)for k,v in test['arms'].items()if k[:2]in('S-','L-')for r in v['records']),
         'notes':['24 shared held-out game seeds, not 96 independent seeds.',
                  'Training has one battle episode per seed/update; entry ordinal cycles deterministically.',
                  'Policy/value loss uses on-policy GAE targets; evaluation MSE uses greedy terminal returns.',
                  'Endpoint HP-equivalent counts terminal defeats as zero; censored pairs are never scored.',
                  'No full-run, high-ascension or multicharacter conclusion.','No external model API calls.']}
 write(out,result)
 print(json.dumps({k:v for k,v in result.items()if k not in ('models','sources','notes')},indent=2))
if __name__=='__main__':main()
