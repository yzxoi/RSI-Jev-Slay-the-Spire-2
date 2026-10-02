#!/usr/bin/env python3
"""E133 standalone learning curves from recorded outcomes, without smoothing."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS = {1701:'#0072B2',1702:'#D55E00'}


def save(fig,directory,name):
    for ext in ('png','svg'):
        fig.savefig(directory/f'{name}.{ext}',dpi=160,facecolor='white')
    plt.close(fig)


def plots(training,directory,test=None):
    directory=Path(directory)
    directory.mkdir(exist_ok=True,parents=True)
    t=json.loads(Path(training).read_text())
    fig,axs=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
    for row in t['learners']:
        us=[u for u in row['updates'] if 'optimization' in u]
        x=np.cumsum([u['summary']['n'] for u in us])
        color=COLORS[row['learner']]
        label=f"S / {row['learner']} ({row['parameters']:,} parameters)"
        for ax,key in [(axs[0,0],'loss'),(axs[0,1],'value_loss'),(axs[0,2],'entropy'),(axs[1,2],'kl')]:
            ax.plot(x,[u['optimization'][key] for u in us],color=color,label=label,lw=1.5)
        axs[1,0].plot(x,[u['summary']['mean_reward'] for u in us],color=color,lw=1.5)
        vs=row['validations']
        vx=[sum(u['summary']['n'] for u in us if u['update']<=v['update']) for v in vs]
        for panel,style in [('challenging','-'),('early','--')]:
            vy=[v['panels'][panel]['mean_reward'] if v['passed'] else np.nan for v in vs]
            axs[1,1].plot(vx,vy,style,color=color,marker='o',ms=4,label=f"{row['learner']} {panel}")
        selected=row.get('long_selected')
        if selected:
            ix=next(i for i,v in enumerate(vs) if v['update']==selected['update'])
            axs[1,1].scatter([vx[ix]],[vs[ix]['panels']['challenging']['mean_reward']],s=100,marker='*',
                             color=color,edgecolor='black',zorder=5)
    titles=['PPO total objective','Value loss: 0.5 x MSE to GAE target','Policy entropy (nats)',
            'Sampled training terminal reward','Fixed validation reward (dashed = early)','Approximate policy KL']
    for ax,title in zip(axs.flat,titles):
        ax.set_title(title,fontsize=10)
        ax.set_xlabel('Completed optimized episodes')
        ax.grid(alpha=.2)
    axs[0,1].set_yscale('log')
    axs[1,1].legend(fontsize=8)
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=2,fontsize=9)
    fig.suptitle('E133: more natural battle data at fixed 73,794-parameter capacity\nRaw update means; two learner seeds; stars = validation-selected long-budget checkpoints',fontsize=14)
    save(fig,directory,'training-curves')

    fig,axs=plt.subplots(2,3,figsize=(14,7),constrained_layout=True)
    for row in t['learners']:
        vs=row['validations']
        x=[v['update']*192 for v in vs]
        for i,panel in enumerate(('early','challenging')):
            for j,asc in enumerate((0,5,10)):
                axs[i,j].plot(x,[v['by_difficulty'][f'{panel}:A{asc}']['clears'] for v in vs],
                              color=COLORS[row['learner']],marker='o',label=str(row['learner']))
                axs[i,j].set_title(f'{panel.title()} A{asc}: clears / 8')
                axs[i,j].set_ylim(0,8.4)
                axs[i,j].set_xlabel('Training episodes')
                axs[i,j].grid(alpha=.2)
    fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=2)
    fig.suptitle('Fixed validation by difficulty and panel\n24 independent seeds; early/challenging states from each seed are correlated',fontsize=14)
    save(fig,directory,'validation-difficulty')
    if not test:
        return
    r=json.loads(Path(test).read_text())
    names=list(r['arms'])
    fig,axs=plt.subplots(2,2,figsize=(15,10),constrained_layout=True)
    for row,panel in enumerate(('early','challenging')):
        axs[row,0].barh(names,[r['arms'][name]['panels'][panel]['clears'] for name in names],color='#0072B2')
        axs[row,0].set_xlim(0,48)
        axs[row,0].set_title(f'{panel.title()}: clears / 48')
        ref=[x for x in r['arms']['planner']['records'] if x['panel']==panel]
        for i,name in enumerate(names):
            entries=[x for x in r['arms'][name]['records'] if x['panel']==panel]
            pairs=list(zip(entries,ref))
            if any(x['status'] not in ('clear','defeat') or y['status'] not in ('clear','defeat') for x,y in pairs):
                continue
            ds=[(x['hp'] if x['status']=='clear' else 0)-(y['hp'] if y['status']=='clear' else 0) for x,y in pairs]
            axs[row,1].scatter(ds,[i]*len(ds),alpha=.3,s=17,color='#0072B2')
            axs[row,1].scatter([np.median(ds)],[i],marker='D',s=40,color='black')
        axs[row,1].set_yticks(range(len(names)),names)
        axs[row,1].axvline(0,color='gray',lw=.8)
        axs[row,1].set_title(f'{panel.title()}: paired HP-equivalent vs planner')
        axs[row,1].set_xlabel('Defeats = 0 HP; diamond = median; censored panels unscored')
    fig.suptitle('Held-out E133 combat evaluation — 48 independent seeds shared by all arms\nTwo panels per seed; repeated weights explicitly aliased in report; not full-run wins',fontsize=14)
    save(fig,directory,'heldout-results')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--training',required=True)
    p.add_argument('--test')
    p.add_argument('--output-dir',required=True)
    a=p.parse_args()
    plots(a.training,a.output_dir,a.test)
