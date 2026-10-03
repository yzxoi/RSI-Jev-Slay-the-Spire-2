#!/usr/bin/env python3
"""Complete historical replay with opt-in observer interference/encoding checks."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import uuid
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.engine import Headless
from rsi.trace import Trace,digest
from rsi.checkpoints import file_hash,wire_pairs
from rsi.battle_search import finish
from rsi.run_env import legal_choices,run_outcome
from rsi.rich_observation import observe,rich_encode,ENCODER
from scripts.evaluate_battle_search_e120 import manifest,write,audit


def replay_one(record,mode,v,deadline):
    started=time.monotonic();deadline=min(deadline,started+180)
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'case':record['case'],'mode':mode})
    r=dict(case=record['case'],mode=mode,status='error',steps=0,observations=0,coverage=Counter())
    engine=None; hashes=[];history={};previous=None; state={}
    try:
        path=ROOT/record['trace_path'];wire=path.with_name('wire.jsonl')
        if file_hash(path)!=record['trace_sha256'] or file_hash(wire)!=record['wire.jsonl_sha256']:
            raise ValueError('Source hashes changed')
        pairs=wire_pairs(wire)
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        def send(c):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Observer validation wall cap')
            engine.timeout=min(15,remaining);return engine.send(c)
        for i,(command,expected) in enumerate(pairs):
            if state:
                options=legal_choices(state,history)
                previous=next(c for c in options if c['action']==command)
                if state['decision']=='map_select':history['removed_here']=False
                if command.get('action')=='remove_card':history['removed_here']=True
            state=send(command);r['steps']+=1
            if digest(state)!=digest(expected):raise ValueError(f'Legacy divergence at {i}')
            if mode=='off' or run_outcome(state):continue
            extra=send({'cmd':'get_learning_observation'})
            repeated=send({'cmd':'get_learning_observation'})
            if digest(extra)!=digest(repeated):raise ValueError(f'Unstable observation at {i}')
            if extra.get('map') is not None and digest(extra['map'])!=digest(send({'cmd':'get_map'})):
                raise ValueError('Existing get_map differs')
            rich={**state,'learning':extra};choices=legal_choices(state,history)
            s,a=rich_encode(rich,choices,previous,max_actions=4096)
            if not np.isfinite(s).all() or not np.isfinite(a).all():raise ValueError('Invalid encoded observation')
            if state.get('decision')=='combat_play':
                for p in ('draw','discard'):
                    if len(extra['piles'][p])!=state[p+'_pile_count']:raise ValueError('Pile count mismatch')
            r['observations']+=1;hashes.append(digest(extra))
            r['coverage'][state['decision']]+=1
            for name in ('osty','orbs','piles','map'):
                if extra.get(name):r['coverage'][name]+=1
            trace.write('observation',dict(command_offset=i,legacy_hash=digest(state),extra_hash=digest(extra),encoding_hash=digest(s.tolist())))
        r.update(status='match',outcome=run_outcome(state),final_hash=digest(state),observation_history_hash=digest(hashes))
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started);return r


def main(output):
    if output.exists():raise ValueError('Keep previous evaluation')
    started=time.monotonic();v={**manifest(),'experiment':'E141','encoder':ENCODER}
    source=ROOT/'experiments/E139/bank-v1.json';bank=json.loads(source.read_text())
    records=[r for r in bank['records'] if r['split']=='train' and r['index']==0]
    if len(records)!=15:raise ValueError('Changed fixed cohort')
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    def one(r):
        modes=[replay_one(r,mode,v,started+900) for mode in ('off','on1','on2')]
        stable=modes[1].get('observation_history_hash')==modes[2].get('observation_history_hash')
        row=dict(case=r['case'],character=r['character'],ascension=r['ascension'],modes=modes,
                 passed=all(m['status']=='match' for m in modes) and stable)
        write(directory/(r['case']+'.json'),row)
        print(json.dumps({'case':r['case'],'passed':row['passed'],'errors':[m.get('error') for m in modes]}),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(one,records))
    report=dict(manifest=v,source_sha256=file_hash(source),before_runtime_manifest=json.loads((ROOT/'artifacts/runs/e141-runtime-before/manifest.json').read_text()),
        records=rows,passed=all(r['passed'] for r in rows),seconds=time.monotonic()-started)
    report['audit']=audit(report);report['passed'] &= report['audit']['pass']
    report['summary']=dict(replays=45,states=sum(m['steps'] for r in rows for m in r['modes']),
                          observations=sum(m['observations'] for r in rows for m in r['modes']))
    write(output,report);print(json.dumps({k:report[k] for k in ('passed','seconds','summary','audit')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
