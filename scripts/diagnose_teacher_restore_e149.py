#!/usr/bin/env python3
"""Fixed, scheduling-only replay diagnostic after E149 v1 startup timeouts."""
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
from rsi.checkpoints import wire_pairs
from rsi.root_teacher import rollout
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, write
from scripts.pilot_root_teacher_e149 import checked, version, same_runtime, info
from scripts.pilot_fullpolicy_e140 import load_phase


def main(output, worker_counts=(1,2)):
    if output.exists():raise ValueError('Preserve prior diagnostics')
    torch.set_num_threads(1)
    v=version();p=checked(ROOT/'experiments/E149/plan-v1.json',tracked=True)
    b=checked(ROOT/'experiments/E149/bank-v1.json',tracked=True);same_runtime(p,v)
    model=load_phase(p['checkpoint']);start=time.monotonic();deadline=start+240
    fixtures=[]
    for index in (0,1,10,11,20,21):
        meta=b['roots'][index];root=checked(ROOT/meta['raw']['path'],meta['raw']['sha256'])
        pre=next(x for x in b['preflights'] if x['case']==root['case'])['reference']
        pairs=wire_pairs((ROOT/pre['trace_path']).with_name('wire.jsonl'));n=len(root['prefix'])
        expected=[dict(before=digest(pairs[i-1][1]),action=pairs[i][0],after=digest(pairs[i][1])) for i in range(n,len(pairs))]
        fixtures.append((root,pre,expected))
    rounds=[]
    for workers in worker_counts:
        clock=time.monotonic()
        def one(item):
            root,pre,expected=item
            r=rollout(root,v,model,f'diagnostic:workers{workers}',expected=expected,
                seconds=max(.001,min(30,deadline-time.monotonic())))
            return dict(case=root['case'],result=compact(r),exact=r['status']==pre['status'] and
                r['plan']==expected and r['final_hash']==pre['final_hash'])
        with ThreadPoolExecutor(max_workers=workers) as pool:rs=list(pool.map(one,fixtures))
        rounds.append(dict(workers=workers,records=rs,seconds=time.monotonic()-clock,
            p95_seconds=float(np.quantile([x['result']['seconds'] for x in rs],.95)),
            passed=all(x['exact'] for x in rs)))
        print(json.dumps({k:x for k,x in rounds[-1].items() if k!='records'}),flush=True)
    proof=audit(rounds)
    result=dict(manifest=v,bank=info(ROOT/'experiments/E149/bank-v1.json'),rounds=rounds,
        seconds=time.monotonic()-start,audit=proof,passed=proof['pass'] and
        all(x['passed'] and x['p95_seconds']<=15 for x in rounds) and time.monotonic()-start<=240,
        limitations='Sequential diagnostic rounds confound concurrency with host load/time; no causal speedup claim.')
    write(output,result)
    print(json.dumps({k:result[k] for k in ('passed','seconds','audit')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,nargs='+',choices=(1,2,4),default=[1,2])
    a=p.parse_args();main(a.output,a.workers)
