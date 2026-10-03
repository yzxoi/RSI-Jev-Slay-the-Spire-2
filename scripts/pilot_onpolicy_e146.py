#!/usr/bin/env python3
"""Fresh complete-prefix PPO; fixed training and held-out transfer evaluation."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.checkpoints import file_hash
from rsi.phase_rl import ENCODER,controller
from rsi.ppo import HP,padded,update
from rsi.run_env import run,replay
from scripts.pilot_fullpolicy_e140 import load_phase,save
from scripts.evaluate_battle_search_e120 import manifest,write,audit

CONFIG={**HP,'lr':1e-4,'gae_lambda':1.}
LEARNERS=(1901,1902)
DIFFICULTIES=(0,5,10)
UPDATES=12
WORKERS=8


def reward(record):
    if record['status']=='defeat':return -1.
    if record['status']!='curriculum_clear':raise ValueError('Incomplete trajectory has no learning reward')
    hp,maximum=record['final_hp'],record['final_max_hp']
    if not 0<hp<=maximum:raise ValueError('Invalid natural terminal HP')
    return 1.+.25*hp/maximum


def summary(rows):
    return dict(attempts=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
        independent_game_seeds=len({r['seed'] for r in rows}),
        network_calls=sum(r['network_calls'] for r in rows),planner_calls=sum(r['planner_calls'] for r in rows),
        phases=dict(sum((Counter(r['scenes']) for r in rows),Counter())),
        boss_encounters=sum(r['target_boss_seen'] for r in rows),
        by_ascension={str(a):dict(Counter(r['status'] for r in rows if r['ascension']==a)) for a in DIFFICULTIES})


def behavior_parity(model,trajectories):
    records=[r for trajectory in trajectories for r in trajectory];lp_delta=0.;value_delta=0.
    with torch.inference_mode():
        for start in range(0,len(records),128):
            batch=records[start:start+128]
            dist,value=model(*padded([r['encoded'] for r in batch]))
            lp=dist.log_prob(torch.tensor([r['index'] for r in batch])).numpy()
            lp_delta=max(lp_delta,float(np.max(np.abs(lp-np.asarray([r['logprob'] for r in batch])))))
            value_delta=max(value_delta,float(np.max(np.abs(value.numpy()-np.asarray([r['value'] for r in batch])))))
    if lp_delta>1e-4 or value_delta>1e-4:raise ValueError('Behavior policy changed during collection')
    return dict(max_logprob_error=lp_delta,max_value_error=value_delta,transitions=len(records))


def train(v,output):
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    source=ROOT/'experiments/E140/training-v2.json'
    cp=json.loads(source.read_text())['learners'][1]['bc']
    report=dict(manifest=v,config=CONFIG,source=cp,source_report_sha256=file_hash(source),
                learners=[],final_acceptance_seeds_unused=True)
    started=time.monotonic()
    for learner in LEARNERS:
        torch.manual_seed(learner);rng=np.random.default_rng(learner)
        model=load_phase(cp)
        with torch.no_grad():model.value.weight.zero_();model.value.bias.zero_()
        optimizer=torch.optim.Adam(model.parameters(),lr=CONFIG['lr'])
        row=dict(learner=learner,status='running',parameters=sum(p.numel() for p in model.parameters()),updates=[])
        row['initial']=save(directory/f'{learner}-initial.pt',model,v,'zero-critic-initial')
        row['selected']=row['initial'];report['learners'].append(row)
        clock=time.monotonic();deadline=clock+1200
        for u in range(UPDATES):
            before=row['selected'];configs=[]
            for a in DIFFICULTIES:
                for i in range(16):
                    configs.append(dict(case=f'train-{learner}-u{u:02}-A{a}-{i:02}',
                        seed=f'e146_train_Ironclad_A{a}_u{u:02}_{i:02}',character='Ironclad',ascension=a,
                        split='train',arm='neural_all',learner=learner,update=u+1,
                        sample_seed=learner*1000000+u*48+len(configs)))
            batchclock=time.monotonic()
            def collect(c):
                trajectory=[]
                r=run(c,{**v,'behavior_checkpoint':before},controller=controller(model,c['sample_seed'],trajectory),
                    stop_after_battles=6,seconds=min(180,max(.001,deadline-time.monotonic())))
                return r,trajectory
            model.eval()
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:outputs=list(pool.map(collect,configs))
            rows=[r for r,_ in outputs];trajectories=[t for _,t in outputs]
            item=dict(update=u+1,behavior_checkpoint=before,episodes=rows,summary=summary(rows),
                      collection_seconds=time.monotonic()-batchclock)
            row['updates'].append(item)
            # No censors are silently dropped, and no old-policy batch is reused next update.
            if any(r['status'] not in ('curriculum_clear','defeat') or r['steps']!=len(t) or
                   r['network_calls']!=r['steps'] or r['planner_calls'] for r,t in outputs):
                row.update(status='incomplete_batch',stopped_update=u+1);write(output,report);break
            if time.monotonic()>=deadline:
                row.update(status='budget_before_update',stopped_update=u+1);write(output,report);break
            try:
                item['parity']=behavior_parity(model,trajectories)
                item['rewards']=[reward(r) for r in rows]
                item['reward_mean']=float(np.mean(item['rewards']))
                t0=time.monotonic();model.train()
                item['optimization']=update(model,optimizer,list(zip(trajectories,item['rewards'])),rng,hp=CONFIG)
                item['optimization_seconds']=time.monotonic()-t0;model.eval()
                cp_path=directory/f'{learner}-u{u+1:02}.pt'
                row['selected']=save(cp_path,model,v,f'PPO-six-battle-{u+1}')
                resume=directory/f'{learner}-u{u+1:02}-optimizer.pt'
                torch.save(dict(optimizer=optimizer.state_dict(),numpy_rng=rng.bit_generator.state,
                    torch_rng=torch.get_rng_state(),checkpoint=row['selected'],update=u+1,config=CONFIG),resume)
                item['checkpoint']=row['selected'];item['resume_state']=dict(path=str(resume.resolve().relative_to(ROOT)),sha256=file_hash(resume))
            except Exception as exc:
                row.update(status='optimization_error',error=f'{type(exc).__name__}: {exc}')
                write(output,report);break
            write(output,report)
            print(json.dumps(dict(learner=learner,update=u+1,summary=item['summary'],reward=item['reward_mean'],
                                  optimization=item['optimization'])),flush=True)
        else:row['status']='complete'
        row['seconds']=time.monotonic()-clock
        write(output,report)
    report['seconds']=time.monotonic()-started
    report['source_unchanged']=file_hash(ROOT/cp['path'])==cp['sha256']
    report['audit']=audit(report)
    report['execution_pass']=report['source_unchanged'] and report['audit']['pass'] and all(r['status']=='complete' for r in report['learners'])
    write(output,report);return report


def evaluate(v,training,output):
    trained=json.loads(training.read_text())
    if not trained['execution_pass']:raise ValueError('Incomplete training: no DEV evaluation')
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    arms={'initial':trained['source'],**{str(r['learner']):r['selected'] for r in trained['learners']}}
    models={k:load_phase(cp) for k,cp in arms.items()}
    # Same frozen weights for both tasks, every seed retained, no checkpoint selection.
    configs=[dict(case=f'{horizon}-{arm}-A{a}-{i:02}',seed=f'e146_dev_Ironclad_A{a}_{i:02}',
                  character='Ironclad',ascension=a,index=i,split='dev',arm='neural_all',actor=arm,horizon=horizon)
             for a in DIFFICULTIES for i in range(10) for arm in arms for horizon in ('six','act1')]
    start=time.monotonic();deadline=start+600
    def one(c):
        limits={'stop_after_battles':6} if c['horizon']=='six' else {'stop_after_act':1}
        r=run(c,{**v,'behavior_checkpoint':arms[c['actor']]},controller=controller(models[c['actor']]),
              seconds=min(180,max(.001,deadline-time.monotonic())),**limits)
        if c['index']==0 and r['status'] in ('curriculum_clear','act_clear','defeat'):
            r['verification']=replay(r,v,seconds=min(180,max(.001,deadline-time.monotonic())))
        write(directory/(c['case']+'.json'),r)
        print(json.dumps({k:r[k] for k in ('case','status','steps','completed_battles','target_boss_seen')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:rows=list(pool.map(one,configs))
    by={h:{a:summary([r for r in rows if r['horizon']==h and r['actor']==a]) for a in arms} for h in ('six','act1')}
    report=dict(manifest=v,training_report_sha256=file_hash(training),checkpoints=arms,configs=configs,records=rows,
        by_horizon=by,seconds=time.monotonic()-start,final_acceptance_seeds_unused=True)
    report['weights_unchanged']=all(file_hash(ROOT/cp['path'])==cp['sha256'] for cp in arms.values())
    report['audit']=audit(report)
    report['execution_pass']=report['audit']['pass'] and report['weights_unchanged'] and all(
        r['status'] in ('curriculum_clear','defeat') if r['horizon']=='six' else r['status'] in ('act_clear','defeat') for r in rows) and all(
        r['network_calls']==r['steps'] and r['planner_calls']==0 and
        r.get('verification',{}).get('status','match')=='match' and
        r.get('verification',{}).get('outcome',r['status'])==r['status'] for r in rows)
    base=by['six']['initial'];base_act=by['act1']['initial'];report['gates']={}
    report['paired']={}
    for arm in (str(l) for l in LEARNERS):
        candidate=by['six'][arm];candidate_act=by['act1'][arm]
        gain=candidate['statuses'].get('curriculum_clear',0)-base['statuses'].get('curriculum_clear',0)
        safe=all(candidate['by_ascension'][str(a)].get('curriculum_clear',0)>=base['by_ascension'][str(a)].get('curriculum_clear',0)-1 for a in DIFFICULTIES)
        report['gates'][arm]=dict(six_battle_gain=gain,no_difficulty_regression_over_one=safe,
            first_act_no_regression=candidate_act['statuses'].get('act_clear',0)>=base_act['statuses'].get('act_clear',0))
        paired={}
        for h in ('six','act1'):
            successes=('curriculum_clear',) if h=='six' else ('act_clear',)
            b={r['seed']:r for r in rows if r['actor']=='initial' and r['horizon']==h}
            counts=Counter()
            for r in rows:
                if r['actor']==arm and r['horizon']==h:
                    left=b[r['seed']]['status'] in successes;right=r['status'] in successes
                    counts['gain' if right and not left else 'regression' if left and not right else 'tie']+=1
            paired[h]=dict(counts)
        report['paired'][arm]=paired
    report['expansion_gate']=report['execution_pass'] and all(g['six_battle_gain']>=3 and
        g['no_difficulty_regression_over_one'] and g['first_act_no_regression'] for g in report['gates'].values())
    write(output,report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('train','evaluate'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--training',type=Path);args=p.parse_args()
    if args.output.exists():raise ValueError('Preserve previous report')
    torch.set_num_threads(1)
    v={**manifest(),'experiment':'E146','encoder':ENCODER,'torch':str(torch.__version__),'device':'cpu','workers':WORKERS}
    result=train(v,args.output) if args.mode=='train' else evaluate(v,args.training,args.output)
    print(json.dumps({k:result[k] for k in ('execution_pass','seconds','audit','gates','expansion_gate') if k in result}),flush=True)
