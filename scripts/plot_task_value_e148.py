#!/usr/bin/env python3
"""E148 fixed-epoch TRAIN fits and frozen DEV value calibration."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(training,evaluation,output):
    t=json.loads(training.read_text());e=json.loads(evaluation.read_text());output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    colors={'legacy':'#cf7d36','task':'#188e9c'}
    for row in t['models']:
        axes[0,0].plot([x['epoch'] for x in row['curve']],[x['mse'] for x in row['curve']],
            color=colors[row['arm']],linestyle='-' if row['learner']==2101 else '--',label=f"{row['learner']} {row['arm']}")
    axes[0,0].set(title='TRAIN: fixed actor, critic-only regression',xlabel='Epoch (fixed final checkpoint)',ylabel='Trajectory-balanced MSE')
    axes[0,0].legend(fontsize=8);axes[0,0].grid(alpha=.2)
    labels=list(e['metrics']);x=np.arange(len(labels));m=e['metrics']
    bars=['#939dab' if '210' not in k else colors[k.split('-')[1]] for k in labels]
    values=[m[k]['all']['mse'] for k in labels]
    axes[0,1].bar(x,values,color=bars)
    for i,v in enumerate(values):axes[0,1].text(i,v+.008,f'{v:.3f}',ha='center',fontsize=9)
    axes[0,1].set(title='DEV: 72 unseen seeds / 144 stochastic paths',ylabel='Trajectory-balanced MSE (lower is better)',xticks=x,xticklabels=labels)
    axes[0,1].tick_params(axis='x',labelrotation=25);axes[0,1].grid(axis='y',alpha=.2)
    labels=[k for k in labels if k!='constant'];x=np.arange(len(labels))
    for k in labels:
        axes[1,0].plot([0,5,10],[m[k][f'A{a}']['mse'] for a in (0,5,10)],marker='o',label=k)
    axes[1,0].set(title='DEV error by ascension',xlabel='Ascension',ylabel='Trajectory-balanced MSE',xticks=[0,5,10])
    axes[1,0].legend(fontsize=8);axes[1,0].grid(alpha=.2)
    if all(m[k]['already_six']['n'] for k in labels):
        axes[1,1].bar(x,[m[k]['already_six']['mean_value'] for k in labels],color=['#939dab' if k=='progress_ridge' else colors[k.split('-')[1]] for k in labels])
        target=m[labels[0]]['already_six']['mean_return'];axes[1,1].axhline(target,color='black',linestyle='--',label=f'Realized return {target:.3f}')
        axes[1,1].legend(fontsize=8)
    axes[1,1].set(title='Six battles cleared: pending rewards',ylabel='Mean value prediction',xticks=x,xticklabels=labels)
    axes[1,1].tick_params(axis='x',labelrotation=25);axes[1,1].grid(axis='y',alpha=.2)
    fig.suptitle('E148 | Task-state value ablation; actor and terminal reward unchanged\nNo actor training, search or full-run strength measurement. Same cases for all predictors.')
    for ext in ('png','svg'):fig.savefig(output/f'task-value-results.{ext}',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('training','evaluation','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();main(a.training,a.evaluation,a.output)
