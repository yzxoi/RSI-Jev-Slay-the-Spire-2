#!/usr/bin/env python3
"""Publication artifacts from saved PPO results, never interpolated outcomes."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'S':'#0072B2','L':'#D55E00','E125':'#009E73'}


def plots(training, directory, test=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    r=json.loads(Path(training).read_text());fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
    for row in r['learners']:
        us=[u for u in row['updates'] if 'optimization' in u]
        if not us:continue
        size=row.get('size','E125');seed=row['learner'];color=COLORS[size];style='-' if seed==1701 else '--'
        x=np.cumsum([u['summary']['n'] for u in us]);label=f"{size} / {seed} ({row['parameters']:,} params)"
        for ax,key in [(axes[0,0],'loss'),(axes[0,1],'value_loss'),(axes[0,2],'entropy')]:
            ax.plot(x,[u['optimization'][key] for u in us],style,color=color,label=label,lw=1.5)
        axes[1,0].plot(x,[u['summary']['mean_reward'] for u in us],style,color=color,lw=1.5)
        vs=row['validations']; vx=[sum(u['summary']['n'] for u in us if u['update']<=v['update']) for v in vs]
        # Censored validation rewards summarize terminal cases only; exclude from trend, mark separately.
        vy=[v['summary']['mean_reward'] if v.get('passed',v.get('pass')) else np.nan for v in vs]
        axes[1,1].plot(vx,vy,style,color=color,marker='o',ms=4)
        axes[1,2].plot(x,[u['optimization']['kl'] for u in us],style,color=color,lw=1.5)
        selected=row.get('selected')
        if selected:
            ix=next((i for i,v in enumerate(vs) if v['update']==selected['update']),None)
            if ix is not None: axes[1,1].scatter([vx[ix]],[vy[ix]],marker='*',s=125,color=color,edgecolors='black',zorder=4)
    titles=['PPO total objective (not playing strength)','Value loss (0.5 x MSE to GAE targets)',
            'Policy entropy (nats)','Sampled training terminal reward','Greedy validation terminal reward','Approximate policy KL']
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title,fontsize=11);ax.set_xlabel('Completed training episodes');ax.grid(alpha=.2)
    axes[0,1].set_yscale('log');axes[0,0].axhline(0,color='gray',lw=.5)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=9)
    fig.suptitle('PPO capacity / data pilot — two initialization seeds per size\nRaw update means; no smoothing; stars = validation-selected checkpoints',fontsize=15)
    for ext in ('png','svg'):fig.savefig(directory/f'training-curves.{ext}',dpi=170,facecolor='white')
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),constrained_layout=True)
    for row in r['learners']:
        size=row.get('size','E125');seed=row['learner'];style='-' if seed==1701 else '--';color=COLORS[size]
        vs=row['validations'];us=row['updates']
        x=[sum(u['summary']['n'] for u in us if u['update']<=v['update']) for v in vs]
        label=f'{size} / {seed}'
        axes[0].plot(x,[v['summary']['clears'] for v in vs],style,color=color,marker='o',label=label)
        # Same cases at every checkpoint; all terminal defeats remain zero in this resource proxy.
        hp=[np.mean([q['hp'] if q['status']=='clear' else 0 for q in v['records']])
            if v.get('passed',v.get('pass')) else np.nan for v in vs]
        axes[1].plot(x,hp,style,color=color,marker='o')
        positive=[(xx,v['summary']['mean_reward']) for xx,v in zip(x,vs) if xx>0 and v.get('passed',v.get('pass'))]
        if positive:axes[2].plot(*zip(*positive),style,color=color,marker='o')
    for ax,title in zip(axes,['Validation clears','Validation mean HP-equivalent','Validation reward after first update']):
        ax.set_title(title);ax.set_xlabel('Completed training episodes');ax.grid(alpha=.2)
    axes[0].set_ylim(0,max(v['summary']['n'] for row in r['learners'] for v in row['validations'])+1)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=4)
    fig.suptitle('Validation detail: fixed unseen game seeds; terminal defeats count as zero HP\nRight panel zooms trained checkpoints; original initialization is retained in the main figure',fontsize=13)
    for ext in ('png','svg'):fig.savefig(directory/f'validation-detail.{ext}',dpi=170,facecolor='white')
    plt.close(fig)
    if test:
        t=json.loads(Path(test).read_text());arms=t['arms'];names=list(arms)
        fig,ax=plt.subplots(1,2,figsize=(13,5),constrained_layout=True)
        ax[0].barh(names,[arms[k]['summary']['clears'] for k in names],color=['#666666' if k in ('planner','attack_priority') else COLORS.get(k.split('-')[0],'#009E73') for k in names])
        ax[0].set_xlim(0,arms[names[0]]['summary']['n']);ax[0].set_xlabel('Battle clears / same held-out seeds')
        ref=arms['planner']['records']
        for i,name in enumerate(names):
            rows=arms[name]['records'];ds=[(r['hp'] if r['status']=='clear' else 0)-(b['hp'] if b['status']=='clear' else 0)
                for r,b in zip(rows,ref) if r['status'] in ('clear','defeat') and b['status'] in ('clear','defeat')]
            if len(ds)!=len(ref):continue
            ax[1].scatter(ds,[i]*len(ds),s=20,alpha=.35,color=COLORS.get(name.split('-')[0],'#666666'))
            ax[1].plot([np.median(ds)],[i],marker='D',ms=7,color='black')
        ax[1].set_yticks(range(len(names)),names);ax[1].axvline(0,color='gray',lw=.8);ax[1].set_xlabel('Paired HP-equivalent delta vs planner (diamond = median)')
        fig.suptitle('Held-out third-battle evaluation — defeats = 0; censored cases never scored\nSingle-battle continuations, not full-run wins',fontsize=13)
        for ext in ('png','svg'):fig.savefig(directory/f'heldout-results.{ext}',dpi=170,facecolor='white')
        plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--training',required=True);p.add_argument('--test');p.add_argument('--output-dir',required=True);a=p.parse_args()
    plots(a.training,a.output_dir,a.test)
