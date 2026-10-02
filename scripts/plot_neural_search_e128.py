#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--direct',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
r=json.loads(Path(a.source).read_text());d=json.loads(Path(a.direct).read_text());directory=Path(a.output_dir);directory.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True)
colors=['#0072B2','#D55E00'];labels=[]
for i,row in enumerate(r['models']):
 for j,mode in enumerate(('value','rollout')):
  ev=row['arms'][mode];base=d['arms'][f"L-{row['learner']}"];y=i*2+j;label=f"{row['learner']} / {mode}";labels.append(label)
  ds=[(x['hp']if x['status']=='clear'else 0)-(b['hp']if b['status']=='clear'else 0)for x,b in zip(ev['records'],base['records'])if x['status']in('clear','defeat')and b['status']in('clear','defeat')]
  if len(ds)==len(base['records']):
   axes[0].scatter(ds,[y]*len(ds),s=20,alpha=.4,color=colors[j]);axes[0].plot(np.median(ds),y,'D',color='black')
  axes[1].barh(y,ev['summary']['clears'],color=colors[j]);axes[1].text(ev['summary']['clears'],y,f"  {ev['summary']['clears']}/{len(base['records'])}",va='center')
  axes[2].barh(y,ev['search_summary']['median_battle_seconds'],color=colors[j])
for ax in axes:ax.set_yticks(range(len(labels)),labels);ax.grid(axis='x',alpha=.2)
axes[0].axvline(0,color='gray',lw=.8);axes[0].set_xlabel('HP-equivalent delta vs direct actor\nDiamond = paired median; defeats = 0')
axes[1].set_xlabel('Complete battle clears');axes[1].set_xlim(0,28)
axes[2].set_xlabel('Median battle wall time (seconds)')
fig.suptitle('Frozen policy + PUCT: learned value versus terminal actor rollouts\nSame 24 held-out seeds; 16 simulations at each round entry; no search training',fontsize=14)
for ext in('png','svg'):fig.savefig(directory/f'search-results.{ext}',dpi=170,facecolor='white')
plt.close(fig)
