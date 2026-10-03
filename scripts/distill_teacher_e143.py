#!/usr/bin/env python3
"""Matched search-trajectory versus self-imitation, then unseen actor-only play."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.engine import ROOT
from rsi.checkpoints import file_hash
from rsi.ppo_data import decisions
from rsi.phase_rl import ENCODER,phase_encode,bc_step,controller
from rsi.ppo_actions import ACTION_SPACE
from rsi.ppo_env import episode
from rsi.run_env import run,replay
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.pilot_fullpolicy_e140 import load_phase,save,require_train,MACRO
from scripts.pilot_branch_teacher_e142 import roots
from scripts.collect_fullrun_e139 import summarize


def version():
    return {**manifest(),'experiment':'E143','encoder':ENCODER,'ppo_action_space':ACTION_SPACE,
            'torch':str(torch.__version__),'device':'cpu','torch_threads':1,'workers':8}


def encoded_rows(record,previous=None):
    return [dict(encoded=phase_encode(d['state'],d['choices'],d['previous'],max_actions=4096),index=d['index'],phase=d['state']['decision'])
            for d in decisions(record,previous)]


def data(v):
    path=ROOT/'experiments/E142/teacher-v1.json';teacher=json.loads(path.read_text())
    if not teacher['teacher_gate'] or teacher['manifest']['headless_assembly_sha256']!=v['headless_assembly_sha256']:
        raise ValueError('Teacher gate/engine proof missing')
    fixtures,_=roots();lookup={f['case']:f for f,_ in fixtures};groups={'self':[],'teacher':[]}
    for r in teacher['records']:
        require_train(r)
        for arm,key in (('self','control'),('teacher','selected')):
            rows=encoded_rows(r[key],lookup[r['case']]['previous'])
            if not rows:raise ValueError('Empty reference path')
            groups[arm].append(rows)
    source=json.loads((ROOT/'experiments/E139/bank-v1.json').read_text());anchors=[];records=[]
    for r in source['records']:
        if r['split']!='train':continue
        require_train(r);records.append(r);anchors.extend(encoded_rows(r))
    proof=audit({'teacher':teacher,'anchors':records})
    if not proof['pass']:raise ValueError('Source traces changed')
    info=dict(teacher_sha256=file_hash(path),anchor_source_sha256=file_hash(ROOT/'experiments/E139/bank-v1.json'),
              source_audit=proof,roots=len(fixtures),path_decisions={k:sum(map(len,g)) for k,g in groups.items()},anchor_decisions=len(anchors))
    return groups,[r for r in anchors if r['phase'] in MACRO],[r for r in anchors if r['phase'] not in MACRO],teacher['checkpoint'],info


def train(output):
    v=version();started=time.monotonic();groups,macro,combat,cp,info=data(v)
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    report=dict(manifest=v,source=info,initial=cp,models=[])
    for seed in (1801,1802):
        for arm in ('self','teacher'):
            rng=np.random.default_rng(seed);torch.manual_seed(seed);model=load_phase(cp)
            optimizer=torch.optim.Adam(model.parameters(),lr=1e-4);curve=[];coverage=np.zeros(30,dtype=int)
            for update in range(64):
                if time.monotonic()-started>600:raise TimeoutError('Fixed training cap')
                root_ids=rng.integers(30,size=64);fractions=rng.random(64)
                batch=[]
                for ri,fraction in zip(root_ids,fractions):
                    rows=groups[arm][int(ri)];batch.append(rows[int(fraction*len(rows))]);coverage[ri]+=1
                batch += [macro[int(i)] for i in rng.integers(len(macro),size=32)]
                batch += [combat[int(i)] for i in rng.integers(len(combat),size=32)]
                curve.append(bc_step(model,optimizer,batch))
            checkpoint=save(directory/f'{arm}-{seed}.pt',model,v,f'{arm}-{seed}')
            row=dict(arm=arm,learner=seed,losses=curve,root_examples=coverage.tolist(),checkpoint=checkpoint,
                     parameters=sum(p.numel() for p in model.parameters()))
            report['models'].append(row);write(directory/f'{arm}-{seed}.json',row);write(output,report)
    report['seconds']=time.monotonic()-started;report['complete']=True;write(output,report)
    print(json.dumps({'training_seconds':report['seconds'],'models':len(report['models']),'source':info}),flush=True)


def evaluate(training,output):
    v=version();started=time.monotonic();deadline=started+900
    subprocess.run(['git','ls-files','--error-unmatch',str(training.relative_to(ROOT))],check=True,stdout=subprocess.DEVNULL,cwd=ROOT)
    t=json.loads(training.read_text())
    if not t.get('complete'):raise ValueError('Unfinished training')
    directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    fixtures,_=roots();arms=[(f"{r['arm']}-{r['learner']}",r['checkpoint']) for r in t['models']]+[('initial',t['initial'])]
    report=dict(manifest=v,training_sha256=file_hash(training),arms={},final_acceptance_seeds_unused=True)
    for name,cp in arms:
        model=load_phase(cp);choose=controller(model)
        configs=[dict(case=f'{name}-A{asc}-{i:02}',seed=f'e143_eval_Ironclad_A{asc}_{i:02}',character='Ironclad',ascension=asc,
                      index=i,split='evaluation',arm='neural_all') for asc in range(11) for i in range(2)]
        def full(c):
            r=run(c,v,controller=choose,seconds=min(180,max(.001,deadline-time.monotonic())))
            if name!='initial' and c['index']==0 and c['ascension'] in (0,5,10) and r['status'] in ('victory','defeat'):
                r['verification']=replay(r,v,seconds=min(180,max(.001,deadline-time.monotonic())))
            write(directory/(c['case']+'.json'),r);return r
        with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(full,configs))
        row=dict(records=records,summary=summarize(records),act2=sum(2 in r['acts_seen'] for r in records),
                 act3=sum(3 in r['acts_seen'] for r in records),a0act2=sum(r['ascension']==0 and 2 in r['acts_seen'] for r in records))
        if name!='initial':
            def battle(item):
                f,_=item;r,_=episode(f,v,name,model=model,encoder=phase_encode,seconds=min(30,max(.001,deadline-time.monotonic())))
                r.pop('plan',None);return r
            with ThreadPoolExecutor(max_workers=8) as pool:row['seen_battles']=list(pool.map(battle,fixtures))
            row['seen_clears']=sum(r['status']=='clear' for r in row['seen_battles'])
        report['arms'][name]=row;write(output,report)
        print(json.dumps({'arm':name,'full':row['summary']['statuses'],'act2':row['act2'],'seen_clears':row.get('seen_clears')}),flush=True)
    report['audit']=audit(report)
    report['execution_pass']=report['audit']['pass'] and all(r['status'] in ('victory','defeat') and r.get('verification',{}).get('status','match')=='match'
        for row in report['arms'].values() for r in row['records']) and all(r['status'] in ('clear','defeat') for row in report['arms'].values() for r in row.get('seen_battles',[]))
    b=report['arms']['initial'];report['expansion_gate']=report['execution_pass'] and all(
        report['arms'][f'teacher-{s}']['act2']>=max(report['arms'][f'self-{s}']['act2'],b['act2'])+2 and
        report['arms'][f'teacher-{s}']['a0act2']>=max(report['arms'][f'self-{s}']['a0act2'],b['a0act2']) for s in (1801,1802))
    report['seconds']=time.monotonic()-started;write(output,report)
    print(json.dumps({k:report[k] for k in ('execution_pass','expansion_gate','audit','seconds')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['train','evaluate']);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--training',type=Path);a=p.parse_args();torch.set_num_threads(1)
    output=a.output.resolve()
    if output.exists():raise ValueError('Preserve previous experiment')
    if a.phase=='train':train(output)
    else:evaluate(a.training.resolve(),output)
