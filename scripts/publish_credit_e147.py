#!/usr/bin/env python3
"""Derive compact audit, trace excerpts and plots; no engine or model execution."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from rsi.checkpoints import file_hash,wire_pairs
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import manifest,write


def main(source,output):
    full=json.loads(source.read_text())
    if not full['execution_pass']:raise ValueError('Source audit failed')
    output.mkdir(parents=True,exist_ok=True)
    if (output/'diagnosis-v2.json').exists():raise ValueError('Preserve published result')
    report={k:v for k,v in full.items() if k not in ('episodes','training_fatal','rescoring','dev')}
    report['publication']=dict(manifest=manifest(),raw_diagnosis_path=str(source),raw_diagnosis_sha256=file_hash(source),
        omitted='Per-episode/fatal/rescore detail stays in local raw audit; all raw source hashes also indexed by E146.')
    report['dev']={k:{**{a:b for a,b in v.items() if a!='fatal'},
        'fatal_summary':dict(n=len(v['fatal']),forced=sum(x['choices']==1 for x in v['fatal']),
            actions=dict(Counter(x['action'] for x in v['fatal'])))} for k,v in full['dev'].items()}
    report['rescoring']={}
    for actor in ('1901','1902'):
        rows=[r for x in full['rescoring'] for r in x['rows'] if r['actor']==actor]
        report['rescoring'][actor]={}
        for phase in sorted({r['phase'] for r in rows}):
            r=[x for x in rows if x['phase']==phase]
            report['rescoring'][actor][phase]=dict(n=len(r),argmax_changed=sum(x['argmax_changed'] for x in r),
                mean_old_to_new_kl=float(np.mean([x['old_to_new_kl'] for x in r])))
    report['rescoring_sources']=[{k:v for k,v in x.items() if k!='rows'} for x in full['rescoring']]
    report['late_training']={}
    for actor in (1901,1902):
        rows=[r for r in full['training'] if r['learner']==actor and r['update']>=9]
        pending=[r['six_already_clear'] for r in rows];n=sum(r['n'] for r in pending)
        report['late_training'][str(actor)]=dict(updates=[r['update'] for r in rows],
            ev=[r['all']['explained_variance'] for r in rows],
            already_six_n=n,already_six_mean_value=sum(r['mean_value']*r['n'] for r in pending)/n,
            already_six_mean_return=sum(r['mean_return']*r['n'] for r in pending)/n)
    evaluation=json.loads((ROOT/'experiments/E146/evaluation-v1.json').read_text())
    excerpts=[]
    for seed,actors,lo,hi in [('e146_dev_Ironclad_A5_04',('initial','1901','1902'),0,17),
                             ('e146_dev_Ironclad_A10_09',('initial','1902'),24,36)]:
        for actor in actors:
            record=next(r for r in evaluation['records'] if r['seed']==seed and r['actor']==actor and r['horizon']=='six')
            path=ROOT/record['trace_path'];wire=path.with_name('wire.jsonl')
            if file_hash(path)!=record['trace_sha256'] or file_hash(wire)!=record['wire.jsonl_sha256']:raise ValueError('Changed trace')
            events=[x['data'] for line in path.read_text().splitlines() if (x:=json.loads(line))['kind']=='decision']
            pairs=wire_pairs(wire);rows=[]
            for i in range(lo,min(hi,len(events))):
                event=events[i];s=pairs[i][1];after=pairs[i+1][1]
                if event['before']!=digest(s) or pairs[i+1][0]!=event['chosen']['action']:raise ValueError('Misaligned excerpt')
                rows.append(dict(i=i,state_hash=event['before'],phase=s['decision'],context=s.get('context'),
                    hp=s.get('player',{}).get('hp'),block=s.get('player',{}).get('block'),energy=s.get('energy'),round=s.get('round'),
                    chosen=event['chosen'],hp_after=after.get('player',{}).get('hp'),next_phase=after['decision'],
                    enemies=[dict(name=e['name'],hp=e['hp'],intents=e.get('intents')) for e in s.get('enemies',[])]))
            excerpts.append(dict(case=record['case'],seed=seed,actor=actor,status=record['status'],
                completed_battles=record['completed_battles'],trace_path=record['trace_path'],
                trace_sha256=record['trace_sha256'],wire_sha256=record['wire.jsonl_sha256'],rows=rows))
    report['case_excerpts']=excerpts
    write(output/'diagnosis-v2.json',report)
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    for actor in (1901,1902):
        r=[x for x in full['training'] if x['learner']==actor];u=[x['update'] for x in r]
        axes[0,0].plot(u,[x['all']['explained_variance'] for x in r],marker='o',label=str(actor))
        axes[0,1].plot(u,[x['six_already_clear']['mean_value'] for x in r],marker='o',label=f'{actor}: V')
        axes[0,1].plot(u,[x['six_already_clear']['mean_return'] for x in r],linestyle='--',alpha=.65,label=f'{actor}: return')
    axes[0,0].axhline(0,color='gray',linestyle=':');axes[0,0].set(title='Pre-update value: fresh training paths',xlabel='Update (48 episodes each)',ylabel='Explained variance; zero = constant predictor')
    axes[0,1].set(title='Six battles cleared, still claiming rewards',xlabel='Update',ylabel='Mean predicted / realized terminal return')
    for ax in axes[0]:ax.legend(fontsize=8);ax.grid(alpha=.2)
    phases=full['training_overall']['by_phase'];names=sorted(phases,key=lambda k:phases[k]['n'],reverse=True)
    y=np.arange(len(names));forced=[phases[k]['forced'] for k in names];multi=[phases[k]['multi'] for k in names]
    axes[1,0].barh(y,multi,label='Multiple legal actions');axes[1,0].barh(y,forced,left=multi,label='One legal action',color='#c5cad1')
    axes[1,0].set(yticks=y,yticklabels=names,title='103,127 decisions / 1,152 trajectories',xlabel='Recorded decisions (correlated within trajectories)')
    axes[1,0].invert_yaxis();axes[1,0].legend(fontsize=8)
    labels=['Initial','1901','1902'];wins=[7,7,4];act=[0,0,0];x=np.arange(3);w=.35
    axes[1,1].bar(x-w/2,wins,w,label='Six-battle success');axes[1,1].bar(x+w/2,act,w,label='Act 1 clear',color='#d78b43')
    for i,a,b in zip(x,wins,act):
        axes[1,1].text(i-w/2,a+.3,str(a),ha='center');axes[1,1].text(i+w/2,b+.3,str(b),ha='center')
    axes[1,1].set(xticks=x,xticklabels=labels,ylim=(0,32),ylabel='Successes / 30 shared unseen seeds',title='Greedy DEV: E146 results, no new gameplay')
    axes[1,1].legend();axes[1,1].grid(axis='y',alpha=.2)
    fig.suptitle('E147 | Trace diagnosis: incomplete task state and weak long-horizon feedback\nValue plots are pre-update stochastic TRAIN returns; DEV is greedy. No causal attribution from final outcome.')
    figures=output/'figures';figures.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(figures/f'credit-diagnosis.{ext}',dpi=150)
    plt.close(fig)
    print(json.dumps(dict(path=str(output/'diagnosis-v2.json'),sha256=file_hash(output/'diagnosis-v2.json'),new_game_actions=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.source,a.output)
