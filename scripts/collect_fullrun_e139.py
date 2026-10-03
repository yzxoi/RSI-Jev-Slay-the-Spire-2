#!/usr/bin/env python3
"""Frozen multi-character full-run corpus and three-way capability diagnosis."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import torch
from rsi.engine import CHARACTERS
from rsi.run_env import run,replay
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.retrain_ppo_e133 import load_model

CONFIGS=[dict(case=f'train-{hero}-A{asc}-{i:02}',seed=f'e139_train_{hero}_A{asc}_{i:02}',
              character=hero,ascension=asc,index=i,split='train',arm='planner')
         for hero in CHARACTERS for asc in (0,5,10) for i in range(4)]
CONFIGS += [dict(case=f'dev-A{asc}-{i:02}-{arm}',seed=f'e139_dev_Ironclad_A{asc}_{i:02}',
              character='Ironclad',ascension=asc,index=i,split='dev',arm=arm)
            for asc in range(11) for i in range(2) for arm in ('planner','neural_combat','neural_all')]


def summarize(records):
    return dict(attempts=len(records),statuses=dict(Counter(r['status'] for r in records)),
        median_floor=statistics.median(r['max_floor'] for r in records),
        max_floor=max(r['max_floor'] for r in records),entries=sum(len(r['entries']) for r in records),
        by_act=dict(Counter(str(e['act']) for r in records for e in r['entries'])),
        scenes=dict(sum((Counter(r['scenes']) for r in records),Counter())),
        phase_seconds=dict(sum((Counter(r['phase_seconds']) for r in records),Counter())))


def main(output):
    if output.exists():raise ValueError('Preserve previous bank')
    torch.set_num_threads(1);start=time.monotonic()
    v={**manifest(),'experiment':'E139','torch':str(torch.__version__),'engine_workers':8,'device':'cpu'}
    training_path=ROOT/'experiments/E133/training-v2.json'
    training=json.loads(training_path.read_text());cp=training['learners'][1]['long_selected']
    model=load_model(cp,v);directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    def collect(c):
        r=run(c,v,model=model)
        if c['split']=='train' and c['index']==0 and r['status'] in ('victory','defeat'):
            r['verification']=replay(r,v)
        write(directory/(c['case']+'.json'),r)
        print(json.dumps({k:r[k] for k in ('case','status','steps','max_floor')}|{'entries':len(r['entries']),'error':r.get('error')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(collect,CONFIGS))
    report=dict(manifest=v,configs=CONFIGS,checkpoint=cp,training_source_sha256=file_hash(training_path),
        records=records,summary=summarize(records),seconds=time.monotonic()-start,
        arms={arm:summarize([r for r in records if r['split']=='dev' and r['arm']==arm]) for arm in ('planner','neural_combat','neural_all')},
        heroes={hero:summarize([r for r in records if r['split']=='train' and r['character']==hero]) for hero in CHARACTERS},
        final_acceptance_reserved=True)
    report['audit']=audit(report)
    report['execution_pass']=all(r['status'] in ('victory','defeat') for r in records) and report['audit']['pass'] and all(r.get('verification',{}).get('status','match')=='match' for r in records)
    write(output,report)
    print(json.dumps({k:report[k] for k in ('summary','execution_pass','audit','seconds')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
