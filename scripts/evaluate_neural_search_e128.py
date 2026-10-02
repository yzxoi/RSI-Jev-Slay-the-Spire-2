#!/usr/bin/env python3
"""Fixed E128 inference contrasts. No training or live-game control."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash
from rsi.neural_search import SearchPolicy
from rsi.ppo_env import episode
from scripts.scale_ppo_e127 import bank,entries,load_checkpoint,version
from scripts.pilot_ppo_e125 import paired_delta,summarize,valid
from scripts.evaluate_battle_search_e120 import audit,write


def evaluate(fs,v,model,mode):
    def run(f):
        policy=SearchPolicy(f,v,model,mode)
        r,_=episode(f,v,'E128:'+mode,policy=policy,seconds=240)
        r['inference_seconds']=policy.neural_seconds
        r['neural_calls']=policy.neural_calls
        r['inference_scope']='feature encoding + tensor prep + network forward; includes simulated states'
        if r['status'] in ('clear','defeat'):
            replay,_=episode(f,v,'E128:verify',expected=r['plan'])
            r['verification']=compact(replay)
            r['verification_match']=all(r.get(k)==replay.get(k) for k in ('status','final_hash','transition_hash','steps'))
        r['roots']=policy.roots;r['probes']=policy.probes
        return compact(r)
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(run,fs))
    probes=[p for r in records for p in r['probes']];roots=[p for r in records for p in r['roots']]
    errors=[p['squared_error'] for p in probes if 'squared_error'in p]
    return dict(records=records,summary=summarize(records),
                passed=valid(records) and all(r.get('verification_match')for r in records),
                search_summary=dict(roots=len(roots),probes=len(probes),changed=sum(r['changed_from_actor']for r in roots),
                    maximum_depth=max((r['depth']for r in roots),default=0),
                    median_battle_seconds=statistics.median(r['seconds']for r in records),
                    reset_seconds=sum(p['replay_seconds']for p in probes),
                    probe_seconds=sum(p['seconds']for p in probes),
                    calibration_n=len(errors),calibration_mse=statistics.mean(errors) if errors else None))


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('preflight','test'))
    p.add_argument('--training',default='experiments/E127/training-v1.json');p.add_argument('--direct',default='experiments/E127/test-v1.json')
    p.add_argument('--output',required=True);p.add_argument('--preflight');a=p.parse_args()
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    output=Path(a.output).resolve()
    if output.exists():raise ValueError('Preserve previous evidence')
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    v={**version(),'experiment':'E128','search_limits':dict(simulations=16,c_puct=1.5,max_depth=8,max_rounds=6)}
    b=bank(v);tr=json.loads(Path(a.training).read_text())
    if a.phase=='preflight' and 'learners' not in tr:
        if tr['status']!='complete' or tr['size']!='L' or tr['learner']!=1701:
            raise ValueError('Preflight requires completed L-1701')
        selected=[tr]
    else:
        if not tr['passed'] or not tr['audit']['pass']:raise ValueError('E127 valid training required')
        selected=[r for r in tr['learners'] if r['size']=='L']
    if a.phase=='preflight':selected=selected[:1];fs=entries(b,'val')[:2]
    else:
        pf=json.loads(Path(a.preflight).read_text())
        if not pf['passed'] or not pf['audit']['pass'] or pf['selected']!=[selected[0]['selected']]:
            raise ValueError('Exact selected-model search preflight required')
        fs=entries(b,'test')
    report=dict(manifest=v,training_sha256=file_hash(a.training),phase=a.phase,
                selected=[r['selected']for r in selected],models=[],passed=True)
    write(directory/'selection-before-evaluation.json',report)
    started=time.monotonic()
    for row in selected:
        model=load_checkpoint(row['selected'],v);result=dict(learner=row['learner'],arms={})
        for mode in ('value','rollout'):
            print(json.dumps({'learner':row['learner'],'starting':mode,'cases':len(fs)}),flush=True)
            ev=evaluate(fs,{**v,'checkpoint':row['selected']},model,mode)
            result['arms'][mode]=ev;report['passed'] &= ev['passed']
            write(directory/f"{row['learner']}-{mode}.json",ev)
            print(json.dumps({'learner':row['learner'],'mode':mode,'passed':ev['passed'],
                              **ev['summary'],'search':ev['search_summary']}),flush=True)
        report['models'].append(result)
    if a.phase=='test':
        direct=json.loads(Path(a.direct).read_text());report['direct_sha256']=file_hash(a.direct)
        report['strength_gate']=True;report['value_efficiency_gate']=True
        for row in report['models']:
            learner=row['learner'];val=row['arms']['value'];roll=row['arms']['rollout']
            bases={'direct':direct['arms'][f'L-{learner}'],'planner':direct['arms']['planner'],'rollout':roll}
            row['comparisons']={k:paired_delta(val,ref)if val['passed']and ref['passed']else None for k,ref in bases.items()}
            d=row['comparisons']['direct'];p=row['comparisons']['planner'];r=row['comparisons']['rollout']
            report['strength_gate'] &= bool(d and p and d['clear_delta']>=0 and d['median_hp_delta']>=3 and p['clear_delta']>=0 and p['median_hp_delta']>=-2)
            report['value_efficiency_gate'] &= bool(r and r['clear_delta']>=0 and r['median_hp_delta']>=-2 and
              val['search_summary']['median_battle_seconds']<=.75*roll['search_summary']['median_battle_seconds'])
    report['seconds']=time.monotonic()-started;report['audit']=audit(report);write(output,report)
    print(json.dumps({k:v for k,v in report.items()if k in ('passed','seconds','audit','strength_gate','value_efficiency_gate')}),flush=True)

if __name__=='__main__':main()
