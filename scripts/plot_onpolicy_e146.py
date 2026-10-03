#!/usr/bin/env python3
"""Unsmoothed fresh-prefix training curves and frozen held-out outcomes."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(training,evaluation,output):
    t=json.loads(training.read_text());e=json.loads(evaluation.read_text());output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for learner in t['learners']:
        updates=[u for u in learner['updates'] if 'optimization' in u]
        x=[u['update']*48 for u in updates];label=str(learner['learner'])
        axes[0,0].plot(x,[u['summary']['statuses'].get('curriculum_clear',0)/48 for u in updates],marker='o',label=label)
        axes[0,1].plot(x,[u['reward_mean'] for u in updates],marker='o',label=label)
        axes[0,2].plot(x,[u['optimization']['value_loss'] for u in updates],marker='o',label=label)
        axes[1,0].plot(x,[u['optimization']['policy_loss'] for u in updates],marker='o',label=label)
        axes[1,1].plot(x,[u['optimization']['kl'] for u in updates],marker='o',label=label)
    axes[0,0].set(title='Training: finish 6 battles',ylabel='Success fraction (48 fresh seeds/update)',ylim=(0,1))
    axes[0,1].set(title='Training: terminal prefix reward',ylabel='Mean reward',ylim=(-1,1.3))
    axes[0,2].set(title='Training: critic loss',ylabel='0.5 * squared return error')
    axes[1,0].set(title='Training: clipped policy loss',ylabel='Mean policy loss')
    axes[1,1].set(title='Training: approximate KL',ylabel='Mean KL')
    axes[1,1].axhline(.03,color='gray',linestyle=':',label='Minibatch stop threshold')
    for ax in list(axes.flat)[:5]:
        ax.set_xlabel('Fresh trajectories per learner');ax.grid(alpha=.2);ax.legend(fontsize=8)
    names=list(e['checkpoints']);x=np.arange(len(names));w=.36
    for h,offset,color,title,positive in [('six',-w/2,'#278589','6 battles','curriculum_clear'),('act1',w/2,'#d39040','Full Act 1','act_clear')]:
        values=[e['by_horizon'][h][n]['statuses'].get(positive,0) for n in names]
        axes[1,2].bar(x+offset,values,w,label=title,color=color)
        for pos,val in zip(x+offset,values):axes[1,2].text(pos,val+.4,str(val),ha='center',fontsize=10)
    axes[1,2].set(title='Greedy evaluation: same 30 unseen seeds',xticks=x,xticklabels=names,ylabel='Successes /30',ylim=(0,33))
    axes[1,2].legend();axes[1,2].grid(axis='y',alpha=.2)
    fig.suptitle('E146 | Complete-prefix on-policy PPO, all actions from actor\n115,778 parameters; A0 / A5 / A10; prefix/Act 1 success is not a full-run win')
    for ext in ('png','svg'):fig.savefig(output/f'onpolicy-results.{ext}',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--training',type=Path,required=True);p.add_argument('--evaluation',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();main(a.training,a.evaluation,a.output_dir)
