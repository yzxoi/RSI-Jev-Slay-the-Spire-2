#!/usr/bin/env python3
"""Preserve every failed save and certify its slower canonical reset explicitly."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from rsi.battle_search import compact
from rsi.checkpoints import continuation_path,file_hash
from rsi.ppo_env import episode
from rsi.reset_fallback import PROTOCOL,recovery_valid,source_plan
from rsi.training_bank import entry_map
from scripts.evaluate_battle_search_e120 import audit,write
from scripts.retrain_ppo_e133 import BANK,bank,eligible,read_committed,version


def recover(f,old,v,deadline):
    result=dict(case=f['case'],status='fail',native=False,restore_reason='verified_full_prefix_recovery',
                original_native_failure=old,replays=[])
    def check():
        if time.monotonic()>=deadline:
            raise TimeoutError('Recovery phase budget; no new replay started')
    try:
        if (old['status']!='fail' or not old['native'] or old.get('A',{}).get('status') not in ('clear','defeat')
                or old.get('B',{}).get('status')!='match' or old.get('C1',{}).get('status')=='match'):
            raise ValueError('Failure is not eligible for native-incompatibility recovery')
        saved=old['B']['created_checkpoint']
        if file_hash(ROOT/saved['path'])!=saved['sha256']:
            raise ValueError('Original failed checkpoint bytes changed')
        original = source_plan(f,old['B'],continuation=True)
        battle = source_plan(f,old['A'])
        expected_map = entry_map(f)
        for i in range(2):
            check()
            replay = continuation_path(f,v,f'full-prefix-recovery:{i}','A',original,expected_map)
            replay.pop('steps',None)
            result['replays'].append(replay)
        check()
        replay,_ = episode(f,v,'full-prefix-recovery:ppo',expected=battle)
        result['replays'].append(compact(replay))
        result['status']='match'
        if not recovery_valid(result):
            raise ValueError('Independent full-prefix recovery mismatch')
    except Exception as exc:
        result.update(status='fail',error=f'{type(exc).__name__}: {exc}')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    output=Path(a.output)
    if output.exists():raise ValueError('Preserve previous recovery report')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    v={**version(),'experiment':'E134','scope':'Reset routing compatibility, no strength claim'}
    b=bank(v)
    source=read_committed(a.source,v)
    fs={f['case']:f for f in eligible(b,source['testing'])}
    if source['cases']!=list(fs) or source['bank_sha256']!=file_hash(BANK):
        raise ValueError('Different or incomplete source case set')
    failed=[r for r in source['records'] if r['status']!='match']
    start=time.monotonic()
    deadline=start+300
    with ThreadPoolExecutor(max_workers=8) as pool:
        recoveries=list(pool.map(lambda r:recover(fs[r['case']],r,v,deadline),failed))
    by_case={r['case']:r for r in recoveries}
    records=[by_case.get(r['case'],r) for r in source['records']]
    report=dict(manifest=v,protocol=PROTOCOL,bank_sha256=file_hash(BANK),testing=source['testing'],
                cases=source['cases'],records=records,failed_native_cases=[r['case'] for r in failed],
                source_certificate=dict(path=a.source,sha256=file_hash(a.source)),
                seconds=time.monotonic()-start,passed=all(r['status']=='match' for r in records))
    report['audit']=audit(report)
    report['passed'] &= report['audit']['pass']
    write(output,report)
    print(json.dumps({'passed':report['passed'],'original_native_failures':report['failed_native_cases'],
                      'recovery_statuses':{r['case']:r['status'] for r in recoveries},
                      'native_modes':sum(r['native'] for r in records),'full_prefix_modes':sum(not r['native'] for r in records),
                      'seconds':report['seconds'],'audit':report['audit']}),flush=True)


if __name__=='__main__':main()
