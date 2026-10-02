#!/usr/bin/env python3
"""E127 frozen capacity comparison. No automatic sweep or model promotion."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.battle_search import (baseline_choice, boundary, choices_for, compact, finish, macro_choice)
from rsi.checkpoints import file_hash
from rsi.engine import Headless
from rsi.ppo import ActorCritic, ENCODER_VERSION, HP, update
from rsi.ppo_env import episode
from rsi.trace import Trace, digest
from scripts.evaluate_battle_search_e120 import audit, manifest, write
from scripts.pilot_ppo_e125 import summarize, valid, paired_delta, load_checkpoint as load_e125

SPLITS = {k: [f'e127_20261002_{k}_{i:02}' for i in range(n)]
          for k, n in [('train', 64), ('val', 16), ('test', 24)]}
SIZES = {'S': dict(state_width=128, action_width=64), 'L': dict(state_width=512, action_width=256)}
LEARNERS = (1701, 1702)
BANK = ROOT / 'experiments/E127/fixtures.json'


def pool_map(fn, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fn, items))


def version():
    return {**manifest(), 'experiment': 'E127', 'encoder': ENCODER_VERSION, 'sizes': SIZES,
            'splits': SPLITS, 'learner_seeds': LEARNERS, 'hyperparameters': HP,
            'torch': str(torch.__version__), 'numpy': str(np.__version__), 'device': 'cpu',
            'torch_threads': torch.get_num_threads(), 'engine_workers': 8,
            'scope': 'Single battle from first three natural Ironclad A0 entries; no full runs'}


def collect_seed(config, v):
    started = time.monotonic(); deadline = started + 90
    trace = Trace(ROOT / 'artifacts/runs' / str(uuid.uuid4()), {**v, 'scope': 'E127_fixture', 'config': config})
    result = {**config, 'status': 'error', 'steps': 0, 'entries': []}
    engine = None; previous = None; state = {}; active = False
    prefix = [dict(cmd='start_run', character='Ironclad', seed=config['seed'], ascension=0)]
    try:
        engine = Headless(trace.directory, timeout=10, resource_decisions=True)
        state = engine.send(prefix[0])
        for step in range(701):
            if state.get('decision') == 'game_over':
                result['status'] = 'defeat_before_third_entry'; break
            if active and boundary(state):
                active = False
            if state.get('decision') == 'combat_play' and not active:
                active = True
                ordinal = len(result['entries']) + 1
                context = state['context']; p = state['player']
                result['entries'].append(dict(case=f"{config['case']}-b{ordinal}", seed=config['seed'],
                    seed_index=config['index'], ordinal=ordinal, split=config['split'], character='Ironclad',
                    ascension=0, status='ready', prefix=list(prefix), prefix_hash=digest(prefix),
                    entry_hash=digest(state), previous=previous, floor=context['floor'],
                    room_type=context['room_type'], hp=p['hp'], max_hp=p['max_hp'],
                    enemies=[e['name'] for e in state['enemies']]))
                trace.write('entry', {'ordinal': ordinal, 'state': state})
                if ordinal == 3:
                    result['status'] = 'ready'; break
            if step == 700 or time.monotonic() >= deadline:
                result['status'] = 'fixture_cap'; break
            chosen = baseline_choice(state, previous) if active else macro_choice(state)
            if chosen['action'] not in [c['action'] for c in choices_for(state)]:
                raise ValueError('Illegal fixture action')
            trace.write('selected', {'before': digest(state), 'choice': chosen})
            engine.timeout = max(.01, min(10, deadline-time.monotonic()))
            state = engine.send(chosen['action']); prefix.append(chosen['action']); previous = chosen
            result['steps'] += 1
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finish(trace, result, engine, started)
    # Every entry points to the complete preparation evidence, reset stops at its own prefix.
    for f in result['entries']:
        f.update({k: result[k] for k in ('trace_path', 'trace_sha256', 'wire.jsonl_sha256', 'engine.stderr.log_sha256')})
    return result


def freeze(v, output):
    configs = [dict(case=f'{split}-{i:02}', seed=s, index=i, split=split)
               for split, seeds in SPLITS.items() for i, s in enumerate(seeds)]
    start = time.monotonic(); seeds = pool_map(lambda c: collect_seed(c, v), configs)
    report = dict(manifest=v, seeds=seeds, fixtures=[f for s in seeds for f in s['entries']],
                  seconds=time.monotonic()-start,
                  passed=all(s['entries'] and s['status'] in ('ready', 'defeat_before_third_entry') for s in seeds))
    report['audit'] = audit(report); write(output, report)
    print(json.dumps({'phase':'freeze', 'passed':report['passed'], 'audit':report['audit'],
                      'entry_count':len(report['fixtures']), 'statuses':dict(Counter(s['status'] for s in seeds))}), flush=True)


def bank(v):
    b = json.loads(BANK.read_text())
    if not b['passed'] or [s['seed'] for s in b['seeds']] != [s for rows in SPLITS.values() for s in rows]:
        raise ValueError('Incomplete/replaced frozen bank')
    for k in ('headless_game_sha256', 'headless_assembly_sha256', 'game_dll_sha256'):
        if b['manifest'][k] != v[k]: raise ValueError('Changed engine')
    return b


def entries(b, split, update_index=None):
    result=[]
    for i, seed in enumerate(SPLITS[split]):
        fs=[f for f in b['fixtures'] if f['seed']==seed]
        result.append(fs[-1] if update_index is None else fs[(update_index-1+i)%len(fs)])
    return result


def attack_priority(state, choices, previous, plan):
    choice = baseline_choice(state, previous)
    if state['decision'] != 'combat_play' or choice['action']['action'] == 'use_potion':
        return choice, {'source':'attack_priority_legacy_resource'}
    attacks = {c['index'] for c in state.get('hand',[]) if c.get('type') == 'Attack'}
    available = [c for c in choices if c['action']['action']=='play_card' and c['action']['args']['card_index'] in attacks]
    if available:
        hp={e['index']:e['hp'] for e in state.get('enemies',[])}
        choice=min(available, key=lambda c:(c['action']['args']['card_index'],
            hp.get(c['action']['args'].get('target_index'), 0), c['action']['args'].get('target_index',-1)))
    else:
        choice=next(c for c in choices if c['action']['action']=='end_turn')
    return choice, {'source':'attack_priority'}


def evaluate(fs, v, label, model=None, policy=None, verify=False):
    def run(f):
        r, data = episode(f,v,label,model=model,policy=policy)
        if data and 'reward' in r:
            predictions=[d['value'] for d in data]
            r['value_calibration']={'n':len(data), 'mse':float(np.mean((np.asarray(predictions)-r['reward'])**2)),
                                    'mean_prediction':float(np.mean(predictions)), 'return':r['reward']}
        if verify and r['status'] in ('clear','defeat'):
            replay,_=episode(f,v,label+':verify',expected=r['plan'])
            r['verification']=compact(replay)
            r['verification_match']=all(r.get(k)==replay.get(k) for k in ('status','final_hash','transition_hash','steps'))
        return compact(r)
    records=pool_map(run,fs)
    return dict(label=label,records=records,summary=summarize(records),
                passed=valid(records) and (not verify or all(r.get('verification_match') for r in records)))


def checkpoint(path, model, optimizer, v, size, learner, index):
    torch.save(dict(model=model.state_dict(), optimizer=optimizer.state_dict(), config=model.config,
                    manifest=v,bank_sha256=file_hash(BANK),size=size,learner=learner,update=index),path)
    return dict(path=str(path.relative_to(ROOT)),sha256=file_hash(path),update=index,config=model.config)


def load_checkpoint(cp,v):
    path=ROOT/cp['path']
    if file_hash(path)!=cp['sha256']: raise ValueError('Checkpoint hash mismatch')
    data=torch.load(path,map_location='cpu',weights_only=True)
    if data['bank_sha256']!=file_hash(BANK) or data['manifest']['encoder']!=ENCODER_VERSION:
        raise ValueError('Checkpoint encoder/bank mismatch')
    for k in ('headless_game_sha256','headless_assembly_sha256','game_dll_sha256'):
        if data['manifest'][k]!=v[k]: raise ValueError('Checkpoint engine mismatch')
    model=ActorCritic(**data['config']);model.load_state_dict(data['model']);model.eval();return model


def train(v,b,output,preflight):
    pf=json.loads(Path(preflight).read_text())
    if not pf['evaluation']['passed'] or pf['bank_sha256']!=file_hash(BANK):
        raise ValueError('Preflight required')
    directory=output.with_suffix('')
    directory.mkdir(exist_ok=False)
    report=dict(manifest=v,bank_sha256=file_hash(BANK),learners=[],passed=True)
    for learner in LEARNERS:
        for size in SIZES:
            started=time.monotonic();work=0.
            torch.manual_seed(learner);rng=np.random.default_rng(learner)
            model=ActorCritic(**SIZES[size]);optimizer=torch.optim.Adam(model.parameters(),lr=HP['lr'],eps=1e-5)
            row=dict(size=size,learner=learner,parameters=sum(p.numel() for p in model.parameters()),
                     updates=[],validations=[],checkpoints=[],status='running')
            report['learners'].append(row)
            cp=checkpoint(directory/f'{size}-{learner}-00.pt',model,optimizer,v,size,learner,0)
            row['checkpoints'].append(cp)
            val=evaluate(entries(b,'val'),{**v,'checkpoint':cp},f'{size}:{learner}:val:0',model=model)
            val['update']=0;row['validations'].append(val)
            for index in range(1,25):
                if work>=2400: row['status']='time_cap'; break
                start=time.monotonic()
                def collect(f):
                    seed=int(digest([learner,index,f['case']])[:16],16)
                    return episode(f,{**v,'checkpoint':cp},f'{size}:{learner}:train:{index}',model=model,sample_seed=seed)
                batch=pool_map(collect,entries(b,'train',index))
                records=[compact(r) for r,_ in batch]
                step=dict(update=index,episodes=records,summary=summarize(records))
                if not valid(records):
                    step['optimizer_skipped']=True;row['updates'].append(step);row['status']='invalid';break
                opt=time.monotonic()
                step['optimization']=update(model,optimizer,[(d,r['reward']) for r,d in batch],rng)
                step['optimization_seconds']=time.monotonic()-opt
                step['collection_and_optimization_seconds']=time.monotonic()-start
                work+=step['collection_and_optimization_seconds'];row['updates'].append(step)
                cp=checkpoint(directory/f'{size}-{learner}-{index:02}.pt',model,optimizer,v,size,learner,index)
                row['checkpoints'].append(cp)
                print(json.dumps({'size':size,'learner':learner,'update':index,'work_seconds':work,
                                  'summary':step['summary'],'optimization':step['optimization']}),flush=True)
                if index%6==0:
                    val=evaluate(entries(b,'val'),{**v,'checkpoint':cp},f'{size}:{learner}:val:{index}',model=model)
                    val['update']=index;row['validations'].append(val)
                    print(json.dumps({'size':size,'learner':learner,'validation':index,**val['summary']}),flush=True)
                write(directory/f'{size}-{learner}.json',row)
            else: row['status']='complete'
            vals=[r for r in row['validations'] if r['passed']]
            if vals:
                best=max(vals,key=lambda r:(r['summary']['clears'],r['summary']['mean_reward'],-r['update']))
                row['selected']=next(cp for cp in row['checkpoints'] if cp['update']==best['update'])
            row.update(work_seconds=work,seconds=time.monotonic()-started)
            report['passed'] &= row['status']=='complete' and bool(vals)
            write(directory/f'{size}-{learner}.json',row)
    report['audit']=audit(report);write(output,report)
    print(json.dumps({'phase':'training_complete','passed':report['passed'],'audit':report['audit'],
                      'selected':[{k:r.get(k) for k in ('size','learner','status','selected')} for r in report['learners']]}),flush=True)


def test(v,b,output,training):
    t=json.loads(Path(training).read_text())
    if not t['passed'] or not t['audit']['pass']: raise ValueError('Complete valid training required')
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    write(directory/'selection-before-test.json',{'training_sha256':file_hash(training),
          'models':[{k:r[k] for k in ('size','learner','selected')} for r in t['learners']]})
    report=dict(manifest=v,bank_sha256=file_hash(BANK),training_sha256=file_hash(training),arms={})
    fs=entries(b,'test');start=time.monotonic()
    arms=[('planner',None,None),('attack_priority',None,attack_priority)]
    old=json.loads((ROOT/'experiments/E125/training-v1.json').read_text())
    for r in old['learners']: arms.append((f"E125-{r['learner']}",load_e125(r['selected'],v),None))
    for r in t['learners']: arms.append((f"{r['size']}-{r['learner']}",load_checkpoint(r['selected'],v),None))
    for name,model,policy in arms:
        result=evaluate(fs,v,name,model=model,policy=policy,verify=name[:2] in ('S-','L-'))
        report['arms'][name]=result;write(directory/f'{name}.json',result)
        print(json.dumps({'phase':'test','arm':name,**result['summary'],'passed':result['passed']}),flush=True)
    report['comparisons']={};report['scale_gate']=True;report['capacity_gate']=True
    for learner in LEARNERS:
        l=report['arms'][f'L-{learner}']
        for control in ('planner','attack_priority',f'S-{learner}'):
            ref=report['arms'][control];key=f'L-{learner}_vs_{control}'
            report['comparisons'][key]=paired_delta(l,ref) if l['passed'] and ref['passed'] else None
        comparisons=report['comparisons']
        p=comparisons[f'L-{learner}_vs_planner'];a=comparisons[f'L-{learner}_vs_attack_priority'];s=comparisons[f'L-{learner}_vs_S-{learner}']
        report['scale_gate'] &= bool(p and a and p['clear_delta']>=0 and p['median_hp_delta']>=-2 and a['clear_delta']>=0 and a['median_hp_delta']>=3)
        report['capacity_gate'] &= bool(s and s['clear_delta']>=0 and s['median_hp_delta']>=2)
    report['seconds']=time.monotonic()-start;report['audit']=audit(report);write(output,report)
    print(json.dumps({'scale_gate':report['scale_gate'],'capacity_gate':report['capacity_gate'],'audit':report['audit']}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('freeze','preflight','train','test'))
    p.add_argument('--output',required=True);p.add_argument('--preflight');p.add_argument('--training');args=p.parse_args()
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    output=Path(args.output).resolve()
    if output.exists(): raise ValueError('Do not overwrite evidence')
    v=version()
    if args.phase=='freeze':freeze(v,output)
    else:
        b=bank(v)
        if args.phase=='preflight':
            report=dict(manifest=v,bank_sha256=file_hash(BANK),evaluation=evaluate(entries(b,'val'),v,'preflight',verify=True))
            report['audit']=audit(report);write(output,report);print(json.dumps({'passed':report['evaluation']['passed'],'audit':report['audit']}),flush=True)
        elif args.phase=='train':train(v,b,output,args.preflight)
        else:test(v,b,output,args.training)

if __name__=='__main__': main()
