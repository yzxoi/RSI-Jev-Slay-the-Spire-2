#!/usr/bin/env python3
"""Frozen complete-act policy: reward density before any PPO gradients."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import uuid
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.engine import Headless
from rsi.trace import Trace,digest
from rsi.checkpoints import file_hash,wire_pairs
from rsi.battle_search import finish
from rsi.run_env import run,replay,act_transition
from rsi.phase_rl import ENCODER,controller
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.evaluate_battle_search_e120 import manifest,write,audit


def positive_boundary(v,deadline):
    bank=json.loads((ROOT/'experiments/E139/bank-v1.json').read_text())
    source=next(r for r in bank['records'] if r['case']=='train-Ironclad-A0-01')
    path=ROOT/source['trace_path'];wire=path.with_name('wire.jsonl')
    if file_hash(path)!=source['trace_sha256'] or file_hash(wire)!=source['wire.jsonl_sha256']:
        raise ValueError('Compatibility source changed')
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'known_positive_boundary_compatibility'})
    r=dict(case='known-positive-boundary',status='error',steps=0,source=source)
    start=time.monotonic();engine=None;boss=False
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for c,s in wire_pairs(wire):
            remaining=min(180-(time.monotonic()-start),deadline-time.monotonic())
            if remaining<=0:raise TimeoutError('Compatibility boundary cap')
            engine.timeout=min(15,remaining);state=engine.send(c);r['steps']+=1
            if digest(state)!=digest(s):raise ValueError('Old positive history diverged')
            context=state.get('context') or {}
            if state.get('decision')=='combat_play' and context.get('act')==1 and context.get('room_type')=='Boss':boss=True
            if act_transition(state,1,boss):
                r.update(status='match',outcome='act_clear',final_hash=digest(state),final_context=context);break
        else:raise ValueError('Known positive lacked first-act boundary')
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,start);return r


def summary(rows):
    return dict(attempts=len(rows),independent_game_seeds=len({r['seed'] for r in rows}),
        statuses=dict(Counter(r['status'] for r in rows)),
        positive_base_seeds=sorted({r['seed'] for r in rows if r['status']=='act_clear'}),
        boss_encounters=sum(r['target_boss_seen'] for r in rows),
        phases=dict(sum((Counter(r['scenes']) for r in rows),Counter())),
        network_calls=sum(r['network_calls'] for r in rows),planner_calls=sum(r['planner_calls'] for r in rows))


def main(output):
    if output.exists():raise ValueError('Keep previous report')
    torch.set_num_threads(1);started=time.monotonic();deadline=started+900
    v={**manifest(),'experiment':'E145','encoder':ENCODER,'torch':str(torch.__version__),'device':'cpu','engine_workers':8}
    training=ROOT/'experiments/E140/training-v2.json';cp=json.loads(training.read_text())['learners'][1]['bc'];model=load_phase(cp)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    report=dict(manifest=v,checkpoint=cp,source_training_sha256=file_hash(training),gradient_updates=0,final_acceptance_seeds_unused=True)
    report['compatibility']=positive_boundary(v,deadline)
    write(output,report)
    if report['compatibility']['status']!='match':raise ValueError('Boundary compatibility gate failed; no new cohort started')
    configs=[dict(case=f'A{asc}-{i:02}-{mode}',seed=f'e145_train_Ironclad_A{asc}_{i:02}',character='Ironclad',ascension=asc,index=i,
                  split='train',arm='neural_all',sampling=mode,sample_seed=None if mode=='greedy' else 14500000+asc*10000+i*10+int(mode[-1]))
             for asc in (0,5,10) for i in range(8) for mode in ('greedy','sample0','sample1','sample2','sample3')]
    def one(c):
        choose=controller(model,c['sample_seed'])
        r=run(c,v,controller=choose,stop_after_act=1,seconds=min(180,max(.001,deadline-time.monotonic())))
        if c['sampling']=='greedy' and c['index'] in (0,1) and r['status'] in ('act_clear','defeat'):
            r['verification']=replay(r,v,seconds=min(180,max(.001,deadline-time.monotonic())))
        write(directory/(c['case']+'.json'),r)
        print(json.dumps({k:r[k] for k in ('case','status','steps','target_boss_seen','final_context')}|{'error':r.get('error')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(one,configs))
    report.update(configs=configs,records=rows,summary=summary(rows),seconds=time.monotonic()-started,
        by_ascension={str(a):summary([r for r in rows if r['ascension']==a]) for a in (0,5,10)},
        by_sampling={s:summary([r for r in rows if r['sampling']==s]) for s in ('greedy','sample0','sample1','sample2','sample3')})
    report['checkpoint_unchanged']=file_hash(ROOT/cp['path'])==cp['sha256']
    report['audit']=audit(report)
    report['execution_pass']=report['checkpoint_unchanged'] and report['audit']['pass'] and all(r['status'] in ('act_clear','defeat') and
        r['planner_calls']==0 and r['network_calls']==r['steps'] and r.get('verification',{}).get('status','match')=='match' and
        r.get('verification',{}).get('outcome',r['status'])==r['status'] for r in rows)
    report['reward_density_gate']=report['execution_pass'] and all(len(s['positive_base_seeds'])>=2 for s in report['by_ascension'].values())
    write(output,report);print(json.dumps({k:report[k] for k in ('summary','execution_pass','reward_density_gate','audit','seconds')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
