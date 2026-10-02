#!/usr/bin/env python3
"""Audit inherited menu compatibility and replay the exact original load-stall case."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash,wire_pairs
from rsi.ppo_actions import complete_choices
from rsi.ppo_env import episode
from rsi.ppo_resume import retry_eligible
from rsi.trace import digest
from rsi.training_bank import matched
from scripts.evaluate_battle_search_e120 import audit,write
from scripts.retrain_ppo_e133 import version,bank,snapshots,load_model,read_committed


def inherited_menus(source):
    records=[]
    for row in source['learners']:
        records += [r for u in row['updates'] if 'optimization' in u for r in u['episodes']]
        records += [r for v in row['validations'] for r in v['records']]
    decisions=selections=0
    for r in records:
        path=ROOT/r['trace_path']
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        ds=[q['data'] for q in rows if q['kind']=='decision']
        if any(len(q['candidates'])>128 for q in ds):
            raise ValueError('Unexpected legacy supported menu')
        decisions+=len(ds)
        if any(q['chosen']['action']['action'] in ('select_cards','skip_select') for q in ds):
            states={digest(s):s for _,s in wire_pairs(path.with_name('wire.jsonl')) if s.get('decision')=='card_select'}
            for q in ds:
                if q['before'] in states:
                    if complete_choices(states[q['before']])!=q['candidates']:
                        raise ValueError('Inherited decision menu changed')
                    selections+=1
    return dict(episodes=len(records),decisions=decisions,selection_decisions=selections,passed=True)


def main(output):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    v={**version(),'experiment':'E137'};start=time.monotonic()
    source_path=ROOT/'experiments/E133/training-v1.json'
    source=read_committed(source_path,v)
    menu_proof=read_committed(ROOT/'experiments/E136/validation-v1.json',v)
    if not menu_proof['passed'] or menu_proof['source_training']['sha256']!=file_hash(source_path):
        raise ValueError('E136 migration proof missing')
    menus=inherited_menus(source)
    b=bank(v);ss=snapshots('experiments/E134/recovery-train-v2.json',v,b)
    row=source['learners'][0]
    old=next(r for r in row['updates'][-1]['episodes'] if r['case']=='train-094-b7')
    f=next(f for f in b['fixtures'] if f['case']==old['case'])
    cp=row['checkpoints'][-1]
    if cp['update']!=13 or not retry_eligible(old,[],ss[f['case']]):
        raise ValueError('Frozen timeout is not eligible')
    model=load_model(cp,v);sample=int(digest([1701,14,f['case']])[:16],16)
    report=dict(manifest=v,source_training=dict(path=str(source_path.relative_to(ROOT)),sha256=file_hash(source_path)),
                action_space_proof_sha256=file_hash(ROOT/'experiments/E136/validation-v1.json'),
                inherited_menus=menus,original_failure=old,timeout_eligible=True,checkpoint=cp,repeats=[])
    first=None
    for i in range(3):
        primary,_=episode(f,{**v,'checkpoint':cp},f'original_stall_case:{i}',model=model,
                          sample_seed=sample,checkpoint=ss[f['case']])
        item=dict(primary=compact(primary),same_sampled_path=first is None or matched(first,primary))
        if primary['status'] in ('clear','defeat'):
            replay,_=episode(f,v,f'independent_full_prefix:{i}',expected=primary['plan'])
            item.update(replay=compact(replay),replay_match=matched(primary,replay))
        report['repeats'].append(item)
        if first is None:first=primary
    report['passed']=menus['passed'] and all(x.get('replay_match') and x['same_sampled_path'] for x in report['repeats'])
    report['audit']=audit(report);report['passed'] &= report['audit']['pass']
    report['seconds']=time.monotonic()-start
    write(output,report)
    print(json.dumps({k:report[k] for k in ('passed','timeout_eligible','inherited_menus','audit','seconds')}
                     |{'outcomes':[x['primary']['status'] for x in report['repeats']]}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.output).exists():raise ValueError('Preserve old evidence')
    main(Path(a.output))
