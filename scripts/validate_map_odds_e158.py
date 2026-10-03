#!/usr/bin/env python3
"""Recertify unchanged native files and frozen paths after the odds-load fix."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact
from rsi.map_prefix import identity
from rsi.research_restore import ENGINE_KEYS
from rsi.root_teacher import rollout
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.pilot_root_teacher_e149 import checked,info,cpu

SOURCE=ROOT/'experiments/E157/capture-v1.json'


def pool(fn,items):
    with ThreadPoolExecutor(max_workers=4) as p:return list(p.map(fn,items))


def main(output):
    if output.exists():raise ValueError('Preserve previous attempts')
    torch.set_num_threads(1)
    v={**manifest(),'experiment':'E158'};source=checked(SOURCE,tracked=True)
    old=source['manifest']
    unchanged=all(v[k]==old[k] for k in ENGINE_KEYS if k!='headless_assembly_sha256')
    if not unchanged or v['headless_assembly_sha256']==old['headless_assembly_sha256']:
        raise ValueError('Expected adapter-only runtime change')
    started,c0=time.monotonic(),cpu();directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    def budget(limit):
        if time.monotonic()-started>=900 or cpu()-c0>=1800:raise TimeoutError('Recertification budget')
        return max(.001,min(limit,900-(time.monotonic()-started)))
    def fixture(ref):
        root=checked(ROOT/ref['root']['path'],ref['root']['sha256'])
        snap={**ref['snapshot'],'engine':{k:v[k] for k in ENGINE_KEYS},
              'recertified_from':digest(ref['snapshot'])}
        identity(root,snap,v)
        return root,snap
    def check(ref,loaded):
        row=dict(case=ref['case'],status='error',checks=[])
        try:
            root,snap=fixture(ref)
            for pair in ref['paths']:
                plan=checked(ROOT/pair['plan']['path'],pair['plan']['sha256'])
                for repeat in range(2 if loaded else 1):
                    r=rollout(root,v,None,f'{"loaded" if loaded else "fresh"}:{pair["arm"]}:{repeat}',
                        snapshot=snap if loaded else None,expected=plan,full=True,seconds=budget(90))
                    row['checks'].append(dict(arm=pair['arm'],repeat=repeat,result=compact(r),
                        exact=r['status']==pair['A']['status'] and r['plan']==plan and r['final_hash']==pair['A']['final_hash']))
            identity(root,snap,v)
            row['status']='complete' if all(x['exact'] for x in row['checks']) else 'mismatch'
        except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'
        write(directory/(ref['case'].replace(':','-')+('-loaded' if loaded else '-fresh')+'.json'),row)
        print({'case':ref['case'],'loaded':loaded,'status':row['status']},flush=True)
        return row
    fresh=pool(lambda ref:check(ref,False),source['records'])
    fresh_ok=len(fresh)==30 and all(x['status']=='complete' and len(x['checks'])==2 for x in fresh)
    loaded=pool(lambda ref:check(ref,True),source['records']) if fresh_ok else []
    loaded_ok=len(loaded)==30 and all(x['status']=='complete' and len(x['checks'])==4 for x in loaded)
    timings=[]
    if loaded_ok:
        def timed(ref):
            row=dict(case=ref['case'],status='error',pairs=[])
            try:
                root,snap=fixture(ref)
                for repeat in range(2):
                    pair=dict(repeat=repeat,order=['A','C'] if (ref['index']+repeat)%2==0 else ['C','A']);row['pairs'].append(pair)
                    for mode in pair['order']:
                        r=rollout(root,v,None,f'timing:{mode}:{repeat}',restore_only=True,
                            snapshot=snap if mode=='C' else None,seconds=budget(30));pair[mode]=compact(r)
                        if r['status']!='restored' or r['final_hash']!=root['root_hash']:raise ValueError('Invalid timing path')
                    pair['speedup']=pair['A']['restore_seconds']/pair['C']['restore_seconds']
                row['status']='complete'
            except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'
            write(directory/(ref['case'].replace(':','-')+'-timing.json'),row)
            return row
        timings=pool(timed,source['records'])
    timing_ok=len(timings)==30 and all(x['status']=='complete' for x in timings)
    stats={}
    if timing_ok:
        pairs=[p for x in timings for p in x['pairs']]
        for mode in ('A','C'):
            a=[p[mode]['restore_seconds'] for p in pairs];stats[mode]=dict(median=float(np.median(a)),p95=float(np.quantile(a,.95)))
        stats['median_paired_speedup']=float(np.median([p['speedup'] for p in pairs]))
    proof=audit([source,fresh,loaded,timings]);seconds=time.monotonic()-started;used=cpu()-c0
    fidelity=fresh_ok and loaded_ok and proof['pass']
    passed=fidelity and timing_ok and seconds<=900 and used<=1800 and stats['median_paired_speedup']>=2 and stats['C']['p95']<=stats['A']['p95']
    result=dict(manifest=v,source=info(SOURCE),source_bank=source['source_bank'],fresh=fresh,loaded=loaded,timings=timings,
        stats=stats,audit=proof,seconds=seconds,cpu_seconds=used,fidelity_pass=fidelity,passed=passed,
        proprietary_game_and_stubs_unchanged=unchanged,
        snapshots=[fixture(ref)[1] for ref in source['records']] if passed else [],
        final_acceptance_seeds_unused=True)
    write(output,result);print({k:result[k] for k in ('passed','fidelity_pass','stats','seconds','cpu_seconds','audit')},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
