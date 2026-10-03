#!/usr/bin/env python3
"""Bounded full-phase BC, offline AWR and fresh PPO experiment."""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.checkpoints import file_hash,wire_pairs
from rsi.trace import digest
from rsi.ppo import ActorCritic,HP,update
from rsi.ppo_data import decisions
from rsi.phase_rl import ENCODER,phase_encode,extend_model,bc_step,offline_fit,controller
from rsi.ppo_env import episode
from rsi.ppo_actions import ACTION_SPACE
from rsi.run_env import run,replay
from scripts.collect_fullrun_e139 import summarize
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.retrain_ppo_e133 import load_model,training_pool,panel_entries
from scripts.pilot_ppo_e125 import summarize as battle_summary

MACRO={'map_select','event_choice','rest_site','shop','potion_reward','card_reward','bundle_select'}


def require_train(record):
    if not record['case'].startswith('train-') or record.get('split','train')!='train':
        raise ValueError('Validation/test record cannot enter training')


def source_data():
    full=json.loads((ROOT/'experiments/E139/bank-v1.json').read_text())
    old=json.loads((ROOT/'experiments/E133/training-v2.json').read_text())
    bank=json.loads((ROOT/'experiments/E133/fixtures-v2.json').read_text())
    fs={f['case']:f for f in bank['fixtures']}
    bc=[];offline=[];new=[];source_records=[]
    for r in full['records']:
        if r['split']!='train':continue
        require_train(r);source_records.append(r)
        if r['status'] not in ('victory','defeat'):raise ValueError('Incomplete BC source')
        ds=decisions(r)
        bc.extend(dict(encoded=phase_encode(d['state'],d['choices'],d['previous'],max_actions=4096),
                       index=d['index'],phase=d['state']['decision']) for d in ds)
        pairs=wire_pairs((ROOT/r['trace_path']).with_name('wire.jsonl'))
        for e in r['entries']:
            prefix=[c for c,_ in pairs[:e['command_count']]]
            if digest(pairs[e['command_count']-1][1])!=e['entry_hash']:raise ValueError('Corrupt entry offset')
            if (r['character']=='Ironclad' or e['ordinal'] in (1,len(r['entries'])) or e['act']==2):
                new.append(dict(case=r['case']+'-b'+str(e['ordinal']),prefix=prefix,prefix_hash=digest(prefix),
                                entry_hash=e['entry_hash'],previous=e['previous'],character=r['character'],ascension=r['ascension']))
    for u in old['learners'][0]['updates'][28:32]:
        for r in u['episodes']:
            require_train(r);source_records.append(r)
            if r['status'] not in ('clear','defeat'):raise ValueError('Incomplete offline target')
            for d in decisions(r,fs[r['case']]['previous']):
                offline.append(dict(encoded=phase_encode(d['state'],d['choices'],d['previous'],max_actions=4096),
                                    index=d['index'],**{'return':r['reward']}))
    iron=[f for s in bank['seeds'] if s['split']=='train' for f in training_pool(s['entries'])]
    iron += [f for f in new if f['character']=='Ironclad']
    others=[f for f in new if f['character']!='Ironclad']
    source_audit=audit(source_records)
    if not source_audit['pass']:raise ValueError('Source audit failed')
    return bc,offline,iron,others,dict(source_audit=source_audit,bc_decisions=len(bc),
        offline_transitions=len(offline),offline_episodes=768,iron_entries=len(iron),other_entries=len(others),
        sources={p:file_hash(ROOT/p) for p in ('experiments/E139/bank-v1.json','experiments/E133/training-v2.json','experiments/E133/fixtures-v2.json')})


def save(path,model,v,label):
    torch.save(dict(model=model.state_dict(),config=model.config,manifest=v,label=label),path)
    return dict(path=str(path.relative_to(ROOT)),sha256=file_hash(path),label=label,config=model.config)


def train(v,output):
    start=time.monotonic();bc,offline,iron,others,info=source_data()
    macro=[r for r in bc if r['phase'] in MACRO];combat=[r for r in bc if r['phase'] not in MACRO]
    directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    source=json.loads((ROOT/'experiments/E133/training-v2.json').read_text())
    report=dict(manifest=v,data=info,learners=[],preprocessing_seconds=time.monotonic()-start)
    for old in source['learners']:
        learner=old['learner'];torch.manual_seed(learner);rng=np.random.default_rng(learner)
        model=extend_model(load_model(old['long_selected'],v));optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
        row=dict(learner=learner,parameters=sum(p.numel() for p in model.parameters()),bc_curve=[],updates=[],status='running')
        clock=time.monotonic()
        for epoch in range(8):
            losses=[]
            for _ in range((len(bc)+127)//128):
                batch=[macro[int(i)] for i in rng.integers(len(macro),size=64)]
                batch += [combat[int(i)] for i in rng.integers(len(combat),size=64)]
                losses.append(bc_step(model,optimizer,batch))
            row['bc_curve'].append(dict(epoch=epoch,loss=float(np.mean(losses))))
        row['bc_seconds']=time.monotonic()-clock;row['bc']=save(directory/f'{learner}-bc.pt',model,v,'BC')
        off=copy.deepcopy(model);offopt=torch.optim.Adam(off.parameters(),lr=3e-4);clock=time.monotonic()
        row['awr_curve']=offline_fit(off,offopt,offline,macro,rng)
        row['awr_seconds']=time.monotonic()-clock;row['awr']=save(directory/f'{learner}-awr.pt',off,v,'AWR')
        optimizer=torch.optim.Adam(model.parameters(),lr=HP['lr']);online_start=time.monotonic()
        for index in range(8):
            batch=[iron[(index*48+i)%len(iron)] for i in range(48)]
            batch += [others[(index*16+i)%len(others)] for i in range(16)]
            def collect(item):
                i,f=item
                return episode(f,v,f'{learner}:PPO:{index+1}',model=model,encoder=phase_encode,
                    sample_seed=learner*100000+index*64+i,seconds=min(30,max(.001,1800-(time.monotonic()-online_start))))
            with ThreadPoolExecutor(max_workers=8) as pool:outputs=list(pool.map(collect,enumerate(batch)))
            results=[r for r,_ in outputs];u=dict(update=index+1,episodes=[{k:val for k,val in r.items() if k!='plan'} for r in results])
            row['updates'].append(u)
            if not all(r['status'] in ('clear','defeat') for r in results):
                row['status']='stopped_incomplete_batch';break
            clock=time.monotonic();u['optimization']=update(model,optimizer,[(data,r['reward']) for r,data in outputs],rng)
            u['macro_bc_loss']=[]
            for _ in range(4):u['macro_bc_loss'].append(bc_step(model,optimizer,[macro[int(i)] for i in rng.integers(len(macro),size=64)],.1))
            u['optimization_seconds']=time.monotonic()-clock
            u['checkpoint']=save(directory/f'{learner}-ppo-{index+1}.pt',model,v,'PPO+macroBC')
            print(json.dumps(dict(phase='PPO',learner=learner,update=index+1,summary=battle_summary(results))),flush=True)
        else:row['status']='complete'
        row['online_seconds']=time.monotonic()-online_start
        row['ppo']=save(directory/f'{learner}-ppo-final.pt',model,v,'PPO+macroBC')
        report['learners'].append(row)
        write(directory/f'{learner}.json',row)
    report['seconds']=time.monotonic()-start;report['passed']=all(r['status']=='complete' for r in report['learners'])
    report['audit']=audit(report);write(output,report)
    print(json.dumps(dict(phase='training_complete',passed=report['passed'],seconds=report['seconds'],audit=report['audit'])),flush=True)


def load_phase(cp):
    path=ROOT/cp['path']
    if file_hash(path)!=cp['sha256']:raise ValueError('Changed phase checkpoint')
    d=torch.load(path,map_location='cpu',weights_only=True)
    if d['manifest']['encoder']!=ENCODER:raise ValueError('Wrong phase encoder')
    model=ActorCritic(**d['config']);model.load_state_dict(d['model']);model.eval();return model


def evaluate(v,training_path,output):
    import subprocess
    subprocess.run(['git','ls-files','--error-unmatch',str(training_path.relative_to(ROOT))],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    training=json.loads(training_path.read_text())
    if not training['audit']['pass']:raise ValueError('Bad training audit')
    start=time.monotonic();bank=json.loads((ROOT/'experiments/E133/fixtures-v2.json').read_text())
    old=json.loads((ROOT/'experiments/E133/training-v2.json').read_text())
    arms=[(f'{name}-{r["learner"]}',load_phase(r[name])) for r in training['learners'] for name in ('bc','awr','ppo')]
    arms += [('old',load_model(old['learners'][1]['long_selected'],v)),('planner',None)]
    report=dict(manifest=v,training_sha256=file_hash(training_path),arms={},final_acceptance_reserved=True)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    for name,model in arms:
        configs=[dict(case=f'{name}-A{asc}-{i:02}',seed=f'e140_eval_Ironclad_A{asc}_{i:02}',
            character='Ironclad',ascension=asc,index=i,split='evaluation',arm='planner' if name=='planner' else 'neural_all')
            for asc in range(11) for i in range(2)]
        choose=controller(model) if name not in ('old','planner') else None
        def one(c):
            r=run(c,v,model=model,controller=choose)
            if name not in ('old','planner') and c['index']==0 and c['ascension'] in (0,5,10) and r['status'] in ('victory','defeat'):
                r['verification']=replay(r,v)
            write(directory/(c['case']+'.json'),r);return r
        with ThreadPoolExecutor(max_workers=8) as pool:rs=list(pool.map(one,configs))
        arm=dict(records=rs,summary=summarize(rs),act2=sum(2 in r['acts_seen'] for r in rs),act3=sum(3 in r['acts_seen'] for r in rs))
        if choose is not None:
            def battle(item):
                panel,f=item;r,_=episode(f,v,name+':battle_validation',model=model,encoder=phase_encode)
                return {k:val for k,val in r.items() if k!='plan'}|dict(panel=panel)
            with ThreadPoolExecutor(max_workers=8) as pool:br=list(pool.map(battle,panel_entries(bank,'val')))
            arm['battle_validation']=dict(records=br,summary=battle_summary(br))
        report['arms'][name]=arm;write(directory/(name+'.json'),arm)
        print(json.dumps(dict(phase='evaluation',arm=name,summary=arm['summary'],act2=arm['act2'],act3=arm['act3'])),flush=True)
    report['continuation_gate']={}
    for name in ('awr','ppo'):
        passed=[]
        for learner in (1701,1702):
            a=report['arms'][f'{name}-{learner}'];b=report['arms'][f'bc-{learner}']
            count=lambda arm:sum(2 in r['acts_seen'] for r in arm['records'] if r['ascension']==0)
            passed.append(a['act2']>=b['act2']+2 and count(a)>=count(b) and
                          all(r['status'] in ('victory','defeat') for r in a['records']))
        report['continuation_gate'][name]=all(passed)
    report['audit']=audit(report);report['seconds']=time.monotonic()-start
    report['execution_pass']=report['audit']['pass'] and all(r['status'] in ('victory','defeat') and
        r.get('verification',{}).get('status','match')=='match' for a in report['arms'].values() for r in a['records'])
    write(output,report);print(json.dumps(dict(phase='complete',execution_pass=report['execution_pass'],gate=report['continuation_gate'],audit=report['audit'],seconds=report['seconds'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('train','evaluate'));p.add_argument('--output',type=Path,required=True);p.add_argument('--training',type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve prior output')
    torch.set_num_threads(1);v={**manifest(),'experiment':'E140','encoder':ENCODER,'ppo_action_space':ACTION_SPACE,'torch':str(torch.__version__),'device':'cpu'}
    if a.phase=='train':train(v,a.output)
    else:evaluate(v,a.training.resolve(),a.output)
