#!/usr/bin/env python3
"""One-factor full-run collection ablation: remove forced elite priority."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.engine import CHARACTERS
from rsi.battle_search import macro_choice,choices_for
from rsi.full import fixed_macro
from rsi.run_env import run,replay
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.collect_fullrun_e139 import summarize


def route_macro(state):
    return fixed_macro(state,choices_for(state)) if state['decision']=='map_select' else macro_choice(state)


def main(output):
    if output.exists():raise ValueError('Preserve prior evaluation')
    start=time.monotonic();deadline=start+900;v={**manifest(),'experiment':'E144'}
    directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    configs=[dict(case=f'{arm}-{hero}-A{asc}-{i:02}',seed=f'e144_train_{hero}_A{asc}_{i:02}',
                  character=hero,ascension=asc,index=i,split='train',arm='planner',route_arm=arm)
             for hero in CHARACTERS for asc in (0,5,10) for i in range(2) for arm in ('elite','route')]
    def one(c):
        callback=route_macro if c['route_arm']=='route' else None
        r=run(c,v,macro_controller=callback,seconds=min(180,max(.001,deadline-time.monotonic())))
        if c['index']==0 and c['ascension']==0 and r['status'] in ('victory','defeat'):
            r['verification']=replay(r,v,seconds=min(180,max(.001,deadline-time.monotonic())))
        write(directory/(c['case']+'.json'),r)
        print(json.dumps({k:r[k] for k in ('case','status','steps','max_floor','acts_seen')}|{'error':r.get('error')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=8) as pool:rs=list(pool.map(one,configs))
    report=dict(manifest=v,configs=configs,records=rs,arms={},seconds=time.monotonic()-start)
    for name in ('elite','route'):
        rows=[r for r in rs if r['route_arm']==name]
        report['arms'][name]=dict(summary=summarize(rows),act2=sum(2 in r['acts_seen'] for r in rows),
            act3=sum(3 in r['acts_seen'] for r in rows),ironclad_a0_act2=sum(r['character']=='Ironclad' and r['ascension']==0 and 2 in r['acts_seen'] for r in rows),
            by_hero={hero:summarize([r for r in rows if r['character']==hero]) for hero in CHARACTERS})
    report['audit']=audit(report)
    report['execution_pass']=all(r['status'] in ('victory','defeat') and r.get('verification',{}).get('status','match')=='match' for r in rs) and report['audit']['pass']
    e,r=report['arms']['elite'],report['arms']['route']
    report['collection_gate']=report['execution_pass'] and r['act2']>=e['act2']+3 and r['ironclad_a0_act2']>=e['ironclad_a0_act2']
    write(output,report)
    print(json.dumps({k:report[k] for k in ('execution_pass','collection_gate','audit','seconds')}|{'arrivals':{a:{k:row[k] for k in ('act2','act3','ironclad_a0_act2')} for a,row in report['arms'].items()}}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
