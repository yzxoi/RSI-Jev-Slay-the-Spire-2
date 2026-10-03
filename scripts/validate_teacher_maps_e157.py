#!/usr/bin/env python3
"""Certify native Map plus short-prefix recovery for all frozen teacher roots."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash
from rsi.map_prefix import map_offset, identity
from rsi.root_teacher import rollout
from scripts.evaluate_battle_search_e120 import audit,write
from scripts.pilot_root_teacher_e149 import checked,version,same_runtime,info,cpu
from scripts.pilot_fullpolicy_e140 import load_phase

BANK=ROOT/'experiments/E149/bank-v1.json'
PLAN=ROOT/'experiments/E149/plan-v1.json'


def parallel(fn,items):
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(fn,items))


def context():
    v={**version(),'experiment':'E157'}
    bank=checked(BANK,tracked=True);plan=checked(PLAN,tracked=True)
    same_runtime(bank,v);same_runtime(plan,v)
    return v,bank,load_phase(plan['checkpoint'])


def capture(output):
    v,bank,model=context();started,c0=time.monotonic(),cpu()
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    def one(meta):
        r=dict(case=meta['case'],index=meta['index'],status='error',paths=[])
        try:
            root=checked(ROOT/meta['raw']['path'],meta['raw']['sha256']);offset=map_offset(root)
            r['map_offset']=offset;r['root']=meta['raw']
            for arm in range(2):
                if time.monotonic()-started>=900 or cpu()-c0>=1800:raise TimeoutError('Capture global budget')
                a=rollout(root,v,model,f'A:{arm}',first_action=root['candidate_set']['actions'][arm],
                    sample_seed=None if arm==0 else 15700000+meta['index'],full=True,
                    seconds=max(.001,min(90,900-(time.monotonic()-started))))
                pair=dict(arm=arm,A=compact(a));r['paths'].append(pair)
                if a['status'] not in ('victory','defeat'):raise ValueError('Incomplete A reference')
                path=directory/f'root-{meta["index"]:02}-arm-{arm}-plan.json';write(path,a['plan'])
                pair['plan']=info(path)
                b=rollout(root,v,model,f'B:{arm}',expected=a['plan'],full=True,capture=dict(map_offset=offset),
                    seconds=max(.001,min(90,900-(time.monotonic()-started))))
                pair['B']=compact(b)
                pair['exact']=b['status']==a['status'] and b['plan']==a['plan'] and b['final_hash']==a['final_hash']
                if not pair['exact']:raise ValueError('Save-call side effect or incomplete B')
                if arm==0:r['snapshot']=b['checkpoint']
            r['status']='complete'
        except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
        write(directory/f'root-{meta["index"]:02}.json',r)
        print(json.dumps({k:r.get(k) for k in ('case','status','error')}),flush=True)
        return r
    records=parallel(one,bank['roots']);proof=audit(records);seconds=time.monotonic()-started;used=cpu()-c0
    result=dict(manifest=v,source_bank=info(BANK),source_plan=info(PLAN),records=records,audit=proof,
        seconds=seconds,cpu_seconds=used,passed=len(records)==30 and all(r['status']=='complete' for r in records)
            and proof['pass'] and seconds<900 and used<1800)
    write(output,result);return result


def verify(capture_path,output):
    v,bank,model=context();source=checked(capture_path,tracked=True);same_runtime(source,v)
    if not source['passed'] or source['source_bank']!=info(BANK):raise ValueError('Unverified references')
    started,c0=time.monotonic(),cpu();wall_left=900-source['seconds'];cpu_left=1800-source['cpu_seconds']
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    def budget(limit):
        if time.monotonic()-started>=wall_left or cpu()-c0>=cpu_left:raise TimeoutError('Verification global budget')
        return max(.001,min(limit,wall_left-(time.monotonic()-started)))
    def one(ref):
        row=dict(case=ref['case'],index=ref['index'],status='error',checks=[])
        try:
            root=checked(ROOT/ref['root']['path'],ref['root']['sha256']);snap=ref['snapshot'];identity(root,snap,v)
            for pair in ref['paths']:
                plan=checked(ROOT/pair['plan']['path'],pair['plan']['sha256'])
                for repeat in range(2):
                    r=rollout(root,v,model,f'C:{pair["arm"]}:{repeat}',snapshot=snap,expected=plan,full=True,seconds=budget(90))
                    row['checks'].append(dict(arm=pair['arm'],repeat=repeat,result=compact(r),exact=
                        r['status']==pair['A']['status'] and r['final_hash']==pair['A']['final_hash'] and r['plan']==plan))
            identity(root,snap,v)
            row['status']='complete' if all(c['exact'] for c in row['checks']) else 'mismatch'
        except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'
        write(directory/f'root-{ref["index"]:02}-verification.json',row)
        print(json.dumps(dict(case=row['case'],phase='verify',status=row['status'])),flush=True)
        return row
    records=parallel(one,source['records'])
    fidelity=len(records)==30 and all(r['status']=='complete' and len(r['checks'])==4 for r in records)
    timings=[]
    if fidelity:
        def timed(ref):
            row=dict(case=ref['case'],pairs=[],status='error')
            try:
                root=checked(ROOT/ref['root']['path'],ref['root']['sha256'])
                for repeat in range(2):
                    pair=dict(repeat=repeat,order=['A','C'] if (ref['index']+repeat)%2==0 else ['C','A'])
                    row['pairs'].append(pair)
                    for mode in pair['order']:
                        r=rollout(root,v,model,f'timing:{mode}:{repeat}',restore_only=True,
                            snapshot=ref['snapshot'] if mode=='C' else None,seconds=budget(30))
                        pair[mode]=compact(r)
                        if r['status']!='restored' or r['final_hash']!=root['root_hash']:
                            raise ValueError('Incomplete/mismatched timing restore')
                    pair['speedup']=pair['A']['restore_seconds']/pair['C']['restore_seconds']
                row['status']='complete'
            except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'
            write(directory/(ref['case'].replace(':','-')+'-timing.json'),row)
            return row
        timings=parallel(timed,source['records'])
    seconds=time.monotonic()-started;used=cpu()-c0;proof=audit([source,records,timings])
    timing_ok=len(timings)==30 and all(x['status']=='complete' for x in timings)
    stats={}
    if timing_ok:
        pairs=[p for r in timings for p in r['pairs']]
        for mode in ('A','C'):
            values=[p[mode]['restore_seconds'] for p in pairs]
            stats[mode]=dict(median=float(np.median(values)),p95=float(np.quantile(values,.95)))
        stats['median_paired_speedup']=float(np.median([p['speedup'] for p in pairs]))
    integrity=fidelity and timing_ok and proof['pass'] and seconds+source['seconds']<=900 and used+source['cpu_seconds']<=1800
    passed=integrity and stats['median_paired_speedup']>=2 and stats['C']['p95']<=stats['A']['p95']
    result=dict(manifest=v,source=info(capture_path),records=records,timings=timings,stats=stats,
        audit=proof,seconds=seconds,cpu_seconds=used,cumulative_seconds=seconds+source['seconds'],
        cumulative_cpu_seconds=used+source['cpu_seconds'],fidelity_pass=fidelity and proof['pass'],
        passed=passed,snapshots=[r['snapshot'] for r in source['records']] if passed else [],
        limitations='Exact fixed runtime and roots only. Native Map saves, not arbitrary combat clones; no new independent policy wins.')
    write(output,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('capture','verify'));p.add_argument('--capture',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();torch.set_num_threads(1)
    if a.output.exists():raise ValueError('Preserve earlier attempts')
    r=capture(a.output) if a.mode=='capture' else verify(a.capture,a.output)
    print(json.dumps({k:r[k] for k in ('passed','fidelity_pass','seconds','cpu_seconds','stats','audit') if k in r}),flush=True)
