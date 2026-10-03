#!/usr/bin/env python3
"""Unsmoothed pilot metrics; never combine macro imitation and combat reward."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(training,evaluation,out):
    t=json.loads(training.read_text());e=json.loads(evaluation.read_text());out.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for r in t['learners']:
        name=str(r['learner'])
        axes[0,0].plot([x['epoch']+1 for x in r['bc_curve']],[x['loss'] for x in r['bc_curve']],marker='o',label=name)
        a=[x for x in r['awr_curve'] if x['phase']=='actor']
        axes[0,1].plot([x['epoch']+1 for x in a],[x['loss'] for x in a],marker='o',label=name)
        u=[x for x in r['updates'] if 'optimization' in x]
        axes[1,0].plot([x['update']*64 for x in u],[sum(y['reward'] for y in x['episodes'])/len(x['episodes']) for x in u],marker='o',label=name)
    axes[0,0].set(title='All-phase imitation loss',xlabel='BC epoch',ylabel='Cross entropy')
    axes[0,1].set(title='Offline AWR + macro BC loss',xlabel='Actor epoch',ylabel='Weighted regression loss')
    axes[1,0].set(title='Fresh PPO training reward (battle)',xlabel='New battle episodes',ylabel='Mean terminal reward')
    names=list(e['arms']);values=[e['arms'][x]['act2'] for x in names]
    axes[1,1].barh(names,values,color=['#6e8fa8' if x.startswith('bc') else '#2a9d8f' if x.startswith('awr') else '#cf8746' if x.startswith('ppo') else '#777777' for x in names])
    axes[1,1].set(title='New-seed full runs: reach Act 2 /22',xlabel='Attempts reaching Act 2',xlim=(0,22))
    for i,n in enumerate(names):
        wins=e['arms'][n]['summary']['statuses'].get('victory',0)
        axes[1,1].text(values[i]+.25,i,f'{values[i]}/22; full wins {wins}',va='center',fontsize=8)
    for ax in list(axes.flat)[:3]:ax.legend();ax.grid(alpha=.2)
    fig.suptitle('E140 | Phase-aware BC, offline AWR and fresh PPO\nTraining-time teachers only; full-run evaluation uses network actions')
    for ext in ('png','svg'):fig.savefig(out/f'pilot-results.{ext}',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--training',type=Path,required=True);p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();main(a.training,a.evaluation,a.output_dir)
