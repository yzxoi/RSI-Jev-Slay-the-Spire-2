#!/usr/bin/env python3
"""Read-only E153 training/evaluation summary and plots."""
import json
from collections import Counter
from pathlib import Path
import sys
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import write,audit,manifest

old=json.loads((ROOT/'experiments/E153/training-v1.json').read_text())
t=json.loads((ROOT/'experiments/E153/training-v2.json').read_text())
e=json.loads((ROOT/'experiments/E153/evaluation-v1.json').read_text())
a,b=old['learners'][0],t['learners'][0]
old_model=torch.load(ROOT/a['selected']['path'],weights_only=True)['model']
new_model=torch.load(ROOT/b['updates'][1]['checkpoint']['path'],weights_only=True)['model']
restart=dict(paths_match=all(u['fixture_cases']==v['fixture_cases'] and all(r['transition_hash']==s['transition_hash'] and r['final_hash']==s['final_hash'] for r,s in zip(u['episodes'],v['episodes'])) for u,v in zip(a['updates'],b['updates'])),weights_equal=all(torch.equal(old_model[k],new_model[k]) for k in old_model),duplicate_training_episodes=48)
assert restart['paths_match'] and restart['weights_equal']

def full(rows):
 return dict(n=len(rows),statuses=dict(Counter(r['status'] for r in rows)),act2=sum(2 in r['acts_seen'] for r in rows),act3=sum(3 in r['acts_seen'] for r in rows),boss_entries=sum(z['room_type']=='Boss' for r in rows for z in r['entries']),mean_battles=float(np.mean([r['completed_battles'] for r in rows])),decisions=sum(r['steps'] for r in rows),network_calls=sum(r['network_calls'] for r in rows),planner_calls=sum(r['planner_calls'] for r in rows))

def local(rows):
 return {m:{room:dict(n=len(rs:=[r for r in rows if r['mode']==m and r['reference_room_type']==room]),statuses=dict(Counter(r['status'] for r in rs)),mean_hp_fraction=float(np.mean([r['hp']/r['max_hp'] for r in rs])),actual_rooms=dict(Counter(r['actual_room_type'] for r in rs))) for room in ('Monster','Elite','Boss')} for m in ('combat','prepare')}

out=dict(manifest={**manifest(),'experiment':'E153','mode':'read_only_report'},restart=restart,training_seconds=t['seconds'],evaluation_seconds=e['seconds'],training={},monitors={'initial':full(t['baseline_monitor'])},local={k:local(rs) for k,rs in e['local'].items()},full={k:full(a['records']) for k,a in e['full'].items()},by_difficulty={k:{str(i):full([r for r in a['records'] if r['ascension']==i]) for i in range(11)} for k,a in e['full'].items()},gates=e['gates'],expansion_gate=e['expansion_gate'])
for r in t['learners']:
 rs=[z for u in r['updates'] for z in u['episodes']]
 out['training'][str(r['learner'])]=dict(parameters=r['parameters'],episodes=len(rs),statuses=dict(Counter(z['status'] for z in rs)),transitions=sum(z['steps'] for z in rs),phases=dict(sum((Counter(z['scenes']) for z in rs),Counter())),restore_seconds=sum(z['restore_seconds'] for z in rs),summed_episode_seconds=sum(z['seconds'] for z in rs),optimization_seconds=sum(u['optimization_seconds'] for u in r['updates']),max_logprob_error=max(u['parity']['max_logprob_error'] for u in r['updates']))
 out['monitors'][str(r['learner'])]= {m['stage']:full(m['records']) for m in r['monitors']}
out['audit']=audit({'stopped':old,'training':t,'evaluation':e})
out['stderr_unclassified_failures']=[]
seen=set()
def scan(obj):
 if isinstance(obj,dict):
  if obj.get('trace_path') and obj['trace_path'] not in seen:
   seen.add(obj['trace_path'])
   text=(ROOT/obj['trace_path']).with_name('engine.stderr.log').read_text().casefold()
   if any(z in text for z in ('missingmethodexception','nullreferenceexception','unobserved task exception','[fatal] unhandled','headless visual')) and obj.get('status')!='error':
    out['stderr_unclassified_failures'].append(obj['trace_path'])
  for val in obj.values():scan(val)
 elif isinstance(obj,list):
  for val in obj:scan(val)
scan({'old':old,'training':t,'evaluation':e})
out['sources']={name:file_hash(ROOT/'experiments/E153'/name) for name in ('training-v1.json','training-v2.json','evaluation-v1.json')}
write(ROOT/'artifacts/runs/e153-analysis-v1.json',out)
figdir=ROOT/'experiments/E153/figures';figdir.mkdir(exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(13,3.7))
for r in t['learners']:
 us=r['updates'];xs=[u['update'] for u in us]
 axes[0].plot(xs,[u['reward_mean'] for u in us],marker='o',label=str(r['learner']))
 axes[1].plot(xs,[u['optimization']['value_loss'] for u in us],marker='o',label=str(r['learner']))
 axes[2].plot(range(4),[out['monitors']['initial']['mean_battles']]+[full(m['records'])['mean_battles'] for m in r['monitors']],marker='o',label=str(r['learner']))
for ax in axes[:2]:
 for x in (2.5,4.5):ax.axvline(x,color='gray',ls=':',alpha=.6)
 ax.set_xticks(range(1,7));ax.set_xlabel('PPO update (2 per stage)')
axes[0].set_title('Training return: task mix changes');axes[0].set_ylabel('Mean terminal return')
axes[1].set_title('Critic optimization loss');axes[1].set_ylabel('Value loss')
axes[2].set_title('Full-run DEV: same 9 seeds');axes[2].set_xticks(range(4),['Initial','Monster','Elite','Boss']);axes[2].set_ylabel('Mean real battles cleared')
for ax in axes:ax.grid(alpha=.2);ax.legend()
fig.tight_layout();fig.savefig(figdir/'training.png',dpi=160);fig.savefig(figdir/'training.svg');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,3.8))
labels=['initial','2301','2302'];rooms=['Monster','Elite','Boss'];xs=np.arange(3)
for i,label in enumerate(labels):
 axes[0].bar(xs+(i-1)*.25,[out['local'][label]['combat'][room]['statuses'].get('clear',0) for room in rooms],width=.25,label=label)
axes[0].set_xticks(xs,rooms);axes[0].set_ylim(0,12.8);axes[0].set_ylabel('Clears / 12 natural held-out roots');axes[0].set_title('Local combat, greedy frozen actors');axes[0].legend()
labels=list(out['full']);axes[1].bar(labels,[out['full'][k]['act2'] for k in labels],color=['gray','#2877b5','#e08030','#269861']);axes[1].set_ylabel('Act2 arrivals / 33 new seeds');axes[1].set_title('Full-run TEST: planner has 1 engine error');axes[1].set_ylim(0,max(3,max(out['full'][k]['act2'] for k in labels)+1))
for ax in axes:ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(figdir/'heldout.png',dpi=160);fig.savefig(figdir/'heldout.svg');plt.close(fig)
print(json.dumps(out,ensure_ascii=False,indent=2))
