#!/usr/bin/env python3
"""Frozen-actor collection, matched critic fits, then frozen DEV calibration."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.checkpoints import file_hash,wire_pairs
from rsi.phase_rl import controller,phase_encode
from rsi.run_env import run,replay
from rsi.task_value import PHASES,Progress,task_features,Critic,balanced_weights,metrics,ridge_features,ridge_fit
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.pilot_onpolicy_e146 import reward

LEARNERS=(2101,2102)
ARMS=('legacy','task')
SETTINGS=dict(epochs=24,lr=3e-4,minibatch=512,grad_norm=1.,ridge_alpha=.01,
              workers=8,collection_budget=900,fit_budget=180,evaluation_budget=120)


def configs():
    return [dict(case=f'{split}-A{a}-{i:03}-r{rep}',seed=f'e148_{split}_Ironclad_A{a}_{i:03}',
        character='Ironclad',ascension=a,index=i,repetition=rep,split=split,arm='neural_all',
        sample_seed=148000000+sid*1000000+a*10000+i*10+rep)
        for sid,(split,n) in enumerate((('train',72),('dev',24)))
        for a in (0,5,10) for i in range(n) for rep in range(2)]


def checked(path):
    path=path.resolve()
    subprocess.run(['git','ls-files','--error-unmatch',str(path.relative_to(ROOT))],cwd=ROOT,
                   stdout=subprocess.DEVNULL,check=True)
    return json.loads(path.read_text())


def plan(v,output):
    source=ROOT/'experiments/E146/training-v1.json';cp=json.loads(source.read_text())['source']
    load_phase(cp)
    result=dict(manifest=v,behavior=cp,source_report_sha256=file_hash(source),configs=configs(),settings=SETTINGS,
                final_acceptance_seeds_unused=True)
    write(output,result);return result


def collect(v,plan_path,output):
    frozen=checked(plan_path)
    if frozen['configs']!=configs() or frozen['settings']!=SETTINGS:raise ValueError('Changed frozen protocol')
    model=load_phase(frozen['behavior']);start=time.monotonic();deadline=start+SETTINGS['collection_budget']
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    def one(config):
        progress=Progress(config['ascension']);temporary=[];rows=[]
        base=controller(model,config['sample_seed'],temporary)
        def choose(state,choices,previous):
            context=progress.observe(state);chosen,extra=base(state,choices,previous)
            row=temporary.pop();rows.append((row['encoded'][0],task_features(context),PHASES.index(state['decision'])))
            extra['value_task_context']=context
            return chosen,extra
        record=run(config,{**v,'behavior_checkpoint':frozen['behavior']},controller=choose,
                   stop_after_battles=6,seconds=min(180,max(.001,deadline-time.monotonic())))
        if config['index']==0 and config['repetition']==0 and record['status'] in ('defeat','curriculum_clear'):
            record['verification']=replay(record,v,seconds=min(180,max(.001,deadline-time.monotonic())))
        write(directory/(config['case']+'.json'),record)
        print(json.dumps({k:record[k] for k in ('case','status','steps','completed_battles')}),flush=True)
        return record,rows
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(one,frozen['configs']))
    records=[r for r,_ in results]
    report=dict(manifest=v,plan_sha256=file_hash(plan_path),behavior=frozen['behavior'],settings=SETTINGS,
                records=records,final_acceptance_seeds_unused=True)
    report['audit']=audit(records)
    report['actor_unchanged']=file_hash(ROOT/frozen['behavior']['path'])==frozen['behavior']['sha256']
    report['execution_pass']=report['audit']['pass'] and report['actor_unchanged'] and all(
        r['status'] in ('defeat','curriculum_clear') and r['steps']==len(rows)==r['network_calls'] and
        r['planner_calls']==0 and r.get('verification',{}).get('status','match')=='match' and
        r.get('verification',{}).get('outcome',r['status'])==r['status'] for r,rows in results)
    if report['execution_pass']:
        s=[];task=[];phase=[];case=[];y=[]
        for i,(record,rows) in enumerate(results):
            for state,t,p in rows:s.append(state);task.append(t);phase.append(p);case.append(i);y.append(reward(record))
        path=directory/'tensors.npz'
        np.savez_compressed(path,states=np.stack(s),tasks=np.stack(task),phases=np.asarray(phase,dtype=np.int16),
            case_ids=np.asarray(case,dtype=np.int32),targets=np.asarray(y,dtype=np.float32))
        report['tensors']=dict(path=str(path.relative_to(ROOT)),sha256=file_hash(path),rows=len(y))
        # Independently reconstruct six preselected recorded paths, including live observer metadata.
        parity=[]
        arrays=np.load(path)
        for i,record in enumerate(records):
            if record['index'] or record['repetition']:continue
            pairs=wire_pairs((ROOT/record['trace_path']).with_name('wire.jsonl'))
            events=[x['data'] for line in (ROOT/record['trace_path']).read_text().splitlines() if (x:=json.loads(line))['kind']=='decision']
            observer=Progress(record['ascension']);previous=None;positions=np.flatnonzero(arrays['case_ids']==i)
            for j,event in enumerate(events):
                state=pairs[j][1];ctx=observer.observe(state)
                if event['before']!=digest(state) or pairs[j+1][0]!=event['chosen']['action'] or ctx!=event['value_task_context']:
                    raise ValueError('Wire or progress metadata mismatch')
                expected=phase_encode(state,event['candidates'],previous,max_actions=4096)[0]
                if not np.array_equal(expected,arrays['states'][positions[j]]) or not np.array_equal(task_features(ctx),arrays['tasks'][positions[j]]):
                    raise ValueError('Tensor reconstruction mismatch')
                previous=event['chosen']
            parity.append(dict(case=record['case'],decisions=len(events),exact=True))
        report['tensor_reconstruction']=parity
    report['coverage']={split:dict(trajectories=len(rs),game_seeds=len({r['seed'] for r in rs}),
        statuses=dict(Counter(r['status'] for r in rs)),phases=dict(sum((Counter(r['scenes']) for r in rs),Counter())))
        for split in ('train','dev') for rs in [[r for r in records if r['split']==split]]}
    report['seconds']=time.monotonic()-start
    report['execution_pass'] &= report['seconds']<=SETTINGS['collection_budget']
    write(output,report);return report


def load_data(bank):
    if not bank['execution_pass']:raise ValueError('Incomplete collection')
    meta=bank['tensors'];path=ROOT/meta['path']
    if file_hash(path)!=meta['sha256']:raise ValueError('Changed tensors')
    return {k:v for k,v in np.load(path).items()}


def recover_collected(v,plan_path,directory,output):
    """Recover only an already complete cohort; no engine/model actions or resampling."""
    start=time.monotonic();frozen=checked(plan_path)
    if frozen['configs']!=configs() or frozen['settings']!=SETTINGS:raise ValueError('Changed recovery protocol')
    records=[json.loads((directory/(c['case']+'.json')).read_text()) for c in frozen['configs']]
    for c,r in zip(frozen['configs'],records):
        if any(r[k]!=value for k,value in c.items()) or r['status'] not in ('defeat','curriculum_clear'):
            raise ValueError('Recovery cannot select or substitute incomplete cases')
    raw_audit=audit(records)
    if not raw_audit['pass']:raise ValueError('Changed recovery traces')
    path=directory/'tensors.npz';before=file_hash(path);d={k:x for k,x in np.load(path).items()}
    if len(d['targets'])!=sum(r['steps'] for r in records) or len(np.unique(d['case_ids']))!=576:
        raise ValueError('Incomplete original tensors')
    parity=[];begins=[];ends=[];source_manifest=None
    for i,r in enumerate(records):
        if time.monotonic()-start>180:raise TimeoutError('Read-only recovery budget')
        rows=[json.loads(line) for line in (ROOT/r['trace_path']).read_text().splitlines()]
        header=rows[0]['data'];begins.append(rows[0]['time']);ends.append(rows[-1]['time'])
        if source_manifest is None:source_manifest={k:val for k,val in header.items() if k not in ('config','scope','stop_after_act','stop_after_battles','behavior_checkpoint')}
        if header['code_commit']!=source_manifest['code_commit'] or header['behavior_checkpoint']!=frozen['behavior']:
            raise ValueError('Changed original collection actor/code')
        for key in ('headless_game_sha256','headless_assembly_sha256','game_dll_sha256'):
            if header[key]!=v[key]:raise ValueError('Changed engine for recovery')
        pairs=wire_pairs((ROOT/r['trace_path']).with_name('wire.jsonl'))
        events=[x['data'] for x in rows if x['kind']=='decision'];positions=np.flatnonzero(d['case_ids']==i)
        if len(events)!=r['steps'] or len(positions)!=r['steps'] or len(pairs)!=r['steps']+1:
            raise ValueError('Incomplete action/tensor alignment')
        observer=Progress(r['ascension']);previous=None
        for j,event in enumerate(events):
            state=pairs[j][1];ctx=observer.observe(state);pos=positions[j]
            if event['before']!=digest(state) or pairs[j+1][0]!=event['chosen']['action'] or ctx!=event['value_task_context']:
                raise ValueError('Changed original action or task metadata')
            expected=phase_encode(state,event['candidates'],previous,max_actions=4096)[0]
            if not np.array_equal(expected,d['states'][pos]) or not np.array_equal(task_features(ctx),d['tasks'][pos]):
                raise ValueError('Changed saved state or task tensor')
            if d['phases'][pos]!=PHASES.index(state['decision']) or d['targets'][pos]!=np.float32(reward(r)):
                raise ValueError('Changed label or phase')
            previous=event['chosen']
        if r['network_calls']!=r['steps'] or r['planner_calls'] or r.get('verification',{}).get('status','match')!='match':
            raise ValueError('Original controller or replay failed')
        parity.append(dict(case=r['case'],decisions=len(events),exact=True))
    if file_hash(path)!=before:raise ValueError('Recovery must be read-only')
    span=max(ends)-min(begins);elapsed=time.monotonic()-start
    report=dict(manifest=source_manifest,recovery_manifest=v,plan_sha256=file_hash(plan_path),behavior=frozen['behavior'],settings=SETTINGS,
        records=records,audit=raw_audit,actor_unchanged=file_hash(ROOT/frozen['behavior']['path'])==frozen['behavior']['sha256'],
        tensors=dict(path=str(path.relative_to(ROOT)),sha256=before,rows=len(d['targets'])),tensor_reconstruction=parity,
        recovery_seconds=elapsed,observed_collection_trace_span_seconds=span,
        seconds=SETTINGS['collection_budget'],seconds_kind='Conservative full collection budget charge including recovery; trace span excludes setup/serialization.',
        coverage={split:dict(trajectories=len(rs),game_seeds=len({r['seed'] for r in rs}),statuses=dict(Counter(r['status'] for r in rs)),
                    phases=dict(sum((Counter(r['scenes']) for r in rs),Counter())))
                  for split in ('train','dev') for rs in [[r for r in records if r['split']==split]]},
        final_acceptance_seeds_unused=True,new_recovery_game_actions=0)
    report['execution_pass']=report['actor_unchanged'] and span+elapsed<SETTINGS['collection_budget']
    write(output,report);return report


def fit(v,bank_path,output):
    start=time.monotonic();bank=checked(bank_path);d=load_data(bank);actor=load_phase(bank['behavior'])
    ids=np.array([i for i,r in enumerate(bank['records']) if r['split']=='train'])
    mask=np.isin(d['case_ids'],ids);data={k:x[mask] for k,x in d.items()}
    if len(ids)!=432 or len(set(bank['records'][i]['seed'] for i in ids))!=216:raise ValueError('TRAIN cohort mismatch')
    y=torch.tensor(data['targets']);w=torch.tensor(balanced_weights(data['case_ids']))
    inputs={arm:torch.from_numpy(np.concatenate([data['states'],data['tasks'] if arm=='task' else np.zeros_like(data['tasks'])],1)) for arm in ARMS}
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    report=dict(manifest=v,bank_sha256=file_hash(bank_path),behavior=bank['behavior'],settings=SETTINGS,
                models=[],train_cases=len(ids),dev_rows_used=0,final_acceptance_seeds_unused=True)
    for learner in LEARNERS:
        torch.manual_seed(learner);initial=Critic(actor)
        models={arm:copy.deepcopy(initial) for arm in ARMS}
        optimizers={a:torch.optim.Adam(m.parameters(),lr=SETTINGS['lr']) for a,m in models.items()}
        curves={a:[] for a in ARMS};rng=np.random.default_rng(learner)
        for epoch in range(SETTINGS['epochs']):
            indices=rng.permutation(len(y))
            for offset in range(0,len(y),SETTINGS['minibatch']):
                if time.monotonic()-start>SETTINGS['fit_budget']:raise TimeoutError('Critic fit budget')
                ix=indices[offset:offset+SETTINGS['minibatch']]
                for arm in ARMS:
                    m=models[arm];opt=optimizers[arm];pred=m(inputs[arm][ix]);loss=(w[ix]*(pred-y[ix]).square()).mean()
                    if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                    opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);opt.step()
            with torch.inference_mode():
                for arm in ARMS:
                    pred=models[arm](inputs[arm]);curves[arm].append(dict(epoch=epoch+1,mse=float((w*(pred-y).square()).mean())))
            print(json.dumps(dict(learner=learner,epoch=epoch+1,train_mse={a:curves[a][-1]['mse'] for a in ARMS})),flush=True)
        for arm in ARMS:
            m=models[arm];path=directory/f'{learner}-{arm}.pt'
            torch.save(dict(model=m.state_dict(),manifest=v,learner=learner,arm=arm),path)
            report['models'].append(dict(learner=learner,arm=arm,path=str(path.relative_to(ROOT)),sha256=file_hash(path),
                parameters=sum(p.numel() for p in m.parameters()),curve=curves[arm]))
    features=ridge_features(data['states'],data['tasks'],data['phases'])
    report['baselines']=dict(constant=float((w*y).mean()),ridge=ridge_fit(features,data['targets'],data['case_ids']).tolist())
    report['actor_unchanged']=file_hash(ROOT/bank['behavior']['path'])==bank['behavior']['sha256']
    report['execution_pass']=report['actor_unchanged'] and len(report['models'])==4
    report['seconds']=time.monotonic()-start
    report['execution_pass'] &= report['seconds']<=SETTINGS['fit_budget']
    write(output,report);return report


def evaluate(v,bank_path,training_path,output):
    start=time.monotonic();bank=checked(bank_path);training=checked(training_path)
    if not training['execution_pass'] or training['bank_sha256']!=file_hash(bank_path):raise ValueError('Unfrozen model cohort')
    d=load_data(bank);actor=load_phase(bank['behavior']);ids=[i for i,r in enumerate(bank['records']) if r['split']=='dev']
    mask=np.isin(d['case_ids'],ids);d={k:x[mask] for k,x in d.items()};y=d['targets'];cases=d['case_ids']
    predictions={'constant':np.full(len(y),training['baselines']['constant']),
        'progress_ridge':ridge_features(d['states'],d['tasks'],d['phases'])@training['baselines']['ridge']}
    for cp in training['models']:
        path=ROOT/cp['path']
        if file_hash(path)!=cp['sha256']:raise ValueError('Changed frozen critic')
        model=Critic(actor);model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True)['model']);model.eval()
        x=torch.from_numpy(np.concatenate([d['states'],d['tasks'] if cp['arm']=='task' else np.zeros_like(d['tasks'])],1))
        with torch.inference_mode():predictions[f"{cp['learner']}-{cp['arm']}"]=model(x).numpy()
    goal=d['tasks'][:,2]>=1.;initial=np.zeros(len(y),dtype=bool);fatal=initial.copy()
    for i in ids:
        positions=np.flatnonzero(cases==i);initial[positions[0]]=True
        if bank['records'][i]['status']=='defeat':fatal[positions[-1]]=True
    groups={'all':np.ones(len(y),dtype=bool),'already_six':goal,'initial':initial,'fatal':fatal}
    groups.update({f'phase:{p}':d['phases']==j for j,p in enumerate(PHASES)})
    groups.update({f'A{a}':np.isclose(d['tasks'][:,4],a/10) for a in (0,5,10)})
    report=dict(manifest=v,bank_sha256=file_hash(bank_path),training_sha256=file_hash(training_path),models=training['models'],
        metrics={name:{g:metrics(p[m],y[m],cases[m]) for g,m in groups.items()} for name,p in predictions.items()},
        cases=[],paired={},gates={},final_acceptance_seeds_unused=True)
    for i in ids:
        m=cases==i;record=bank['records'][i]
        report['cases'].append(dict(case=record['case'],seed=record['seed'],ascension=record['ascension'],status=record['status'],
            steps=record['steps'],trace_sha256=record['trace_sha256'],
            mse={n:metrics(p[m],y[m],cases[m])['mse'] for n,p in predictions.items()}))
    seed_names=sorted({r['seed'] for r in report['cases']});rng=np.random.default_rng(148)
    # Two independent action-sampling streams at the identical starting input.
    # This estimates return noise only at starts, not at arbitrary later states.
    start_pairs=[]
    for seed in seed_names:
        ix=[np.flatnonzero(cases==i)[0] for i in ids if bank['records'][i]['seed']==seed]
        if len(ix)!=2 or not np.array_equal(d['states'][ix[0]],d['states'][ix[1]]) or not np.array_equal(d['tasks'][ix[0]],d['tasks'][ix[1]]):
            raise ValueError('Repeated seed has different starting critic inputs')
        start_pairs.append(ix)
    noise=float(np.mean([(float(y[a])-float(y[b]))**2/2 for a,b in start_pairs]))
    report['initial_return_noise']=dict(game_seed_pairs=len(start_pairs),variance_estimate=noise,
        note='Paired-return noise estimate at identical starting inputs only; finite-sample, not a full-trajectory noise floor or gate.',
        initial_mse_minus_noise={k:m['initial']['mse']-noise for k,m in report['metrics'].items()})
    draws=rng.integers(len(seed_names),size=(2000,len(seed_names)))
    goal_seeds={bank['records'][i]['seed'] for i in np.unique(cases[goal])}
    best_simple=min(report['metrics'][b]['all']['mse'] for b in ('constant','progress_ridge'))
    for learner in LEARNERS:
        a=f'{learner}-legacy';b=f'{learner}-task';base=report['metrics'][a];candidate=report['metrics'][b]
        delta=np.array([np.mean([r['mse'][b]-r['mse'][a] for r in report['cases'] if r['seed']==s]) for s in seed_names])
        ci=np.quantile(delta[draws].mean(axis=1),[.025,.975]).tolist()
        report['paired'][str(learner)]=dict(game_seeds=len(seed_names),mean_delta=float(delta.mean()),bootstrap95=ci,
                                           seed_deltas=dict(zip(seed_names,delta.tolist())))
        c,bound=candidate['already_six'],base['already_six']
        gate=dict(ten_percent_vs_legacy=candidate['all']['mse']<=.9*base['all']['mse'],
            five_percent_vs_simple=candidate['all']['mse']<=.95*best_simple,paired_ci_below_zero=ci[1]<0,
            difficulty_guard=all(candidate[f'A{a}']['mse']<=1.1*base[f'A{a}']['mse'] for a in (0,5,10)),
            boundary_coverage=len(goal_seeds)>=10,
            boundary_calibration=bool(c['n'] and c['mae']<=.25 and c['mae']<=.5*bound['mae']))
        report['gates'][str(learner)]={**gate,'pass':all(gate.values())}
    path=output.with_suffix('.npz');np.savez_compressed(path,case_ids=cases,targets=y,**predictions)
    report['predictions']=dict(path=str(path.relative_to(ROOT)),sha256=file_hash(path))
    report['coverage']=dict(dev_trajectories=len(ids),dev_game_seeds=len(seed_names),post_clear_game_seeds=len(goal_seeds),
                           phases={p:int((d['phases']==j).sum()) for j,p in enumerate(PHASES)})
    report['audit']=audit(bank);report['seconds']=time.monotonic()-start
    report['execution_pass']=report['audit']['pass'] and len(ids)==144 and len(seed_names)==72 and report['seconds']<=SETTINGS['evaluation_budget']
    report['expansion_gate']=report['execution_pass'] and all(g['pass'] for g in report['gates'].values())
    write(output,report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('plan','collect','recover','fit','evaluate'))
    for name in ('plan','bank','training','output','collected-dir'):p.add_argument('--'+name,type=Path,required=name=='output')
    a=p.parse_args()
    for key,value in vars(a).items():
        if isinstance(value,Path):setattr(a,key,value.resolve())
    if a.output.exists():raise ValueError('Preserve prior attempts')
    torch.set_num_threads(1)
    v={**manifest(),'experiment':'E148','torch':str(torch.__version__),'numpy':np.__version__,'device':'cpu'}
    if a.mode=='plan':result=plan(v,a.output)
    elif a.mode=='collect':result=collect(v,a.plan,a.output)
    elif a.mode=='recover':result=recover_collected(v,a.plan,a.collected_dir,a.output)
    elif a.mode=='fit':result=fit(v,a.bank,a.output)
    else:result=evaluate(v,a.bank,a.training,a.output)
    print(json.dumps({k:result[k] for k in ('seconds','execution_pass','coverage','gates','expansion_gate') if k in result}),flush=True)
