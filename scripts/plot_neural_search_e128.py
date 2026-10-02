#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--direct',required=True)
p.add_argument('--analysis');p.add_argument('--output-dir',required=True);a=p.parse_args()
r=json.loads(Path(a.source).read_text());d=json.loads(Path(a.direct).read_text());directory=Path(a.output_dir);directory.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True)
colors=['#0072B2','#D55E00'];labels=[]
for i,row in enumerate(r['models']):
 for j,mode in enumerate(('value','rollout')):
  ev=row['arms'][mode];base=d['arms'][f"L-{row['learner']}"];y=i*2+j;label=f"{row['learner']} / {mode}";labels.append(label)
  ds=[(x['hp']if x['status']=='clear'else 0)-(b['hp']if b['status']=='clear'else 0)for x,b in zip(ev['records'],base['records'])if x['status']in('clear','defeat')and b['status']in('clear','defeat')]
  if ds:
   axes[0].scatter(ds,[y]*len(ds),s=20,alpha=.4,color=colors[j]);axes[0].plot(np.median(ds),y,'D',color='black')
  axes[0].text(.98,y+.24,f'{len(ds)}/{len(base["records"])} complete pairs',
               transform=axes[0].get_yaxis_transform(),ha='right',fontsize=8)
  counts=ev['summary']['statuses'];capped=sum(n for s,n in counts.items() if s not in ('clear','defeat'))
  axes[1].barh(y,ev['summary']['clears'],color=colors[j]);axes[1].text(1,y,
    f"{counts.get('clear',0)} clear / {counts.get('defeat',0)} defeat / {capped} censored",va='center',fontsize=8,color='white')
  axes[1].scatter(base['summary']['clears'],y,marker='|',s=150,color='black',zorder=3,
                  label='Direct actor'if y==0 else None)
  axes[2].barh(y,ev['search_summary']['median_battle_seconds'],color=colors[j])
  axes[2].scatter(np.median([x['seconds']for x in base['records']]),y,marker='|',s=150,color='black',zorder=3,
                  label='Direct actor'if y==0 else None)
for ax in axes:
 ax.set_yticks(range(len(labels)),labels);ax.set_ylim(-.6,len(labels)-.4);ax.grid(axis='x',alpha=.2)
axes[0].axvline(0,color='gray',lw=.8);axes[0].set_xlabel('HP-equivalent delta vs direct actor\nComplete pairs only; censored cases omitted\nDiamond = conditional median; defeats = 0')
limit=max(2,*(abs(x)for x in axes[0].get_xlim()));axes[0].set_xlim(-limit,limit)
axes[1].set_xlabel('Complete battle clears');axes[1].set_xlim(0,28)
axes[2].set_xlabel('Median battle wall time (seconds)')
axes[1].legend(fontsize=8,loc='upper right');axes[2].legend(fontsize=8,loc='upper right')
fig.suptitle('Frozen policy + PUCT: learned value versus terminal actor rollouts\nSame 24 held-out seeds; 16 simulations at each round entry; no search training',fontsize=14)
for ext in('png','svg'):fig.savefig(directory/f'search-results.{ext}',dpi=170,facecolor='white')
plt.close(fig)

if a.analysis:
 analysis=json.loads(Path(a.analysis).read_text())
 fig,axes=plt.subplots(1,len(analysis['models']),figsize=(12,5),squeeze=False,constrained_layout=True)
 for ax,row in zip(axes[0],analysis['models']):
  arm=row['arms']['rollout'];xs=arm['calibration_rows']
  actual=np.array([x['actual']for x in xs]);pred=np.array([x['predicted']for x in xs])
  ax.scatter(actual,pred,s=12,alpha=.18,color='#0072B2',edgecolors='none')
  ax.plot([-1,1.25],[-1,1.25],color='black',lw=1,label='Exact calibration')
  ax.axhline(1.25,color='#D55E00',ls='--',lw=.8,label='Maximum possible reward')
  ax.axhline(-1,color='#D55E00',ls='--',lw=.8)
  ax.set_title(f"Learner {row['learner']} | n={len(xs)} leaves\n"
               f"Critic MSE {arm['critic_mse']:.4f}; simple HP comparator {arm['assume_clear_current_hp_mse']:.4f}")
  ax.set_xlabel('Actual greedy-continuation return');ax.set_ylabel('Raw critic prediction (before clamp)')
  ax.grid(alpha=.2);ax.legend(fontsize=8,loc='lower right')
 fig.suptitle('Critic calibration on leaves visited by terminal-rollout search\nDescriptive, correlated samples; the HP comparator assumes a win and is not a policy',fontsize=13)
 for ext in('png','svg'):fig.savefig(directory/f'value-calibration.{ext}',dpi=170,facecolor='white')
 plt.close(fig)
