#!/usr/bin/env python3
"""Exhaustive, descriptive audit of forced terminal decisions in E127 test paths."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.checkpoints import file_hash,wire_pairs
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import write

p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
if out.exists():raise ValueError('Preserve previous diagnostic')
source=ROOT/'experiments/E127/test-v1.json';report=json.loads(source.read_text());rows=[]
for name,arm in report['arms'].items():
 if name[:2] not in ('S-','L-'):continue
 for result in arm['records']:
  if result['status']!='defeat':continue
  path=ROOT/result['trace_path']
  if file_hash(path)!=result['trace_sha256']:raise ValueError('Changed trace')
  decisions=[json.loads(l)['data']for l in path.read_text().splitlines()if json.loads(l)['kind']=='decision']
  last=decisions[-1];pairs=wire_pairs(path.parent/'wire.jsonl');state=pairs[-2][1];after=pairs[-1][1]
  if digest(state)!=last['before'] or digest(after)!=result['final_hash']:raise ValueError('Final transition mismatch')
  rows.append(dict(arm=name,case=result['case'],trace_path=result['trace_path'],trace_sha256=result['trace_sha256'],
      before_hash=digest(state),after_hash=digest(after),candidate_count=len(last['candidates']),
      chosen=last['chosen']['action'],probabilities=last['probabilities'],value_prediction=last['value'],
      actual_terminal_reward=-1.,player_hp=state['player']['hp'],player_block=state['player'].get('block'),
      energy=state.get('energy'),enemies=[{k:e.get(k)for k in ('name','hp','intents')}for e in state.get('enemies',[])],
      terminal_decision=after.get('decision'),victory=after.get('victory')))
write(out,{'source_sha256':file_hash(source),'defeat_final_decisions':rows,
           'notes':['All four selected models and all 24 held-out cases inspected; only actual defeat endpoints listed.',
                    'A one-candidate final state has no remaining policy choice; its immediate outcome is deterministic here.',
                    'This diagnoses a critic error on observed states, not the causal reason an earlier action lost.',
                    'Multiple models/cases may share states; rows are not independent samples.']})
print(json.dumps(rows,indent=2))
