#!/usr/bin/env python3
"""Frozen objective-family pilot; official engine outcomes, never heuristic wins."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import boundary,finish,fixture
from rsi.campaign_teacher import permitted_state
from rsi.checkpoints import file_hash,wire_pairs
from rsi.encounter_objective import OBJECTIVES,ObjectiveProgram
from rsi.engine import Headless
from rsi.research_restore import ENGINE_KEYS
from rsi.run_env import legal_choices,replay
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import manifest,audit,write


def reference(r):
    return {k:r[k] for k in ('case','trace_path','trace_sha256','wire.jsonl_sha256','engine.stderr.log_sha256')}


def freeze(v):
    source=ROOT/'experiments/E160/evaluation-v1.json';e=json.loads(source.read_text());roots=[]
    assert all(v[k]==e['manifest'][k] for k in ENGINE_KEYS)
    for record in e['records']:
        if record['arm']!='astra_campaign':continue
        assert audit([record])['pass']
        path=ROOT/record['trace_path'];pairs=wire_pairs(path.parent/'wire.jsonl')
        seen=set();reservations=[];previous=None
        for line in path.read_text().splitlines():
            event=json.loads(line);d=event['data']
            if event['kind']=='campaign_response':reservations=d['packet']['potion_reservations']
            if event['kind']!='decision':continue
            state=d['state'];ctx=state.get('context',{});key=(ctx.get('act'),ctx.get('floor'))
            if state['decision']=='combat_play' and key not in seen:
                seen.add(key)
                if key[0]==2 or (key[0]==1 and ctx.get('room_type')=='Boss'):
                    idx=next(i for i,(_,s) in enumerate(pairs) if digest(s)==digest(state))
                    end=next(s for _,s in pairs[idx+1:] if boundary(s))
                    roots.append(dict(case=f"{record['case']}-act{key[0]}-floor{key[1]}",source=reference(record),
                        commands=idx+1,prefix_hash=digest([c for c,_ in pairs[:idx+1]]),entry_hash=digest(state),
                        expected_final_hash=digest(end),reservations=reservations,previous=previous,
                        hp=state['player']['hp'],max_hp=state['player']['max_hp'],
                        enemies=[x['name'] for x in state['enemies']],context=ctx))
            previous=d['chosen']
    assert len(roots)==15
    return dict(manifest=v,source_sha256=file_hash(source),objectives=OBJECTIVES,discovery=roots,
        holdout=[dict(case=f'holdout-A{a}-{i:03}',seed=f'e163_holdout_Ironclad_A{a}_{i:03}',character='Ironclad',ascension=a,index=j*2+i)
                 for j,a in enumerate((0,5,10)) for i in range(2)],
        budgets=dict(probe_seconds=120,probe_actions=300,rpc=15,search_seconds=60,workers=4,global_seconds=1200),
        final_acceptance_seeds_unused=True)


def probe(root,v,objective,deadline):
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'E163_objective_probe','case':root['case'],
        'objective':objective,'entry_hash':root['entry_hash'],'prefix_hash':root['prefix_hash']})
    start=time.monotonic();engine=None;state={};previous=root['previous'];trans=[];power_plays=[]
    program=ObjectiveProgram(previous,objective)
    r=dict(case=root['case'],objective=objective,status='error',steps=0,run_id=trace.directory.name)
    def send(command):
        left=min(120-(time.monotonic()-start),deadline-time.monotonic())
        if left<=0:raise TimeoutError('Probe/global cap')
        engine.timeout=min(15,left);return engine.send(command)
    try:
        assert audit([root['source']])['pass']
        pairs=wire_pairs((ROOT/root['source']['trace_path']).parent/'wire.jsonl')[:root['commands']]
        assert digest([c for c,_ in pairs])==root['prefix_hash']
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch at {i}')
        assert digest(state)==root['entry_hash'];r['restore_seconds']=time.monotonic()-start
        for step in range(301):
            end=boundary(state)
            if end:r['status']=end;break
            if step==300:raise TimeoutError('Battle action cap')
            choices=legal_choices(state,{})
            masked,blocked=permitted_state(state,root['reservations'])
            chosen,meta=program.choose(masked,choices,previous) if len(choices)>1 else (choices[0],{})
            assert chosen['action'] in [c['action'] for c in choices]
            cmd=chosen['action'];before=digest(state)
            if cmd['action']=='use_potion':assert cmd['args']['potion_index'] not in blocked
            if cmd['action']=='play_card':
                card=next(c for c in state['hand'] if c['index']==cmd['args']['card_index'])
                if card['type']=='Power':power_plays.append(dict(round=state['round'],name=card['name']))
            trace.write('decision',dict(state=state,chosen=chosen,blocked=blocked,**meta))
            program.remember(state,chosen);previous=chosen
            if state['decision']=='combat_play':r['last_round']=state['round']
            state=send(cmd);r['steps']+=1
            trans.append(dict(before=before,action=cmd,after=digest(state)))
        r.update(final_hash=digest(state),transition_hash=digest(trans),hp=state['player']['hp'],
            potions=[p['id'] for p in state['player']['potions']],power_plays=power_plays,
            recorded_boundary_match=digest(state)==root.get('expected_final_hash') if objective=='baseline' and root.get('expected_final_hash') else None)
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,start);return r


def rank(r):
    if r['status'] not in ('clear','defeat'):return (-1,0,0)
    return (int(r['status']=='clear'),r['hp']+4*len(r['potions']) if r['status']=='clear' else 0,-r['steps'])


def parallel(fn,items):
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(fn,items))


def evaluate_roots(roots,v,deadline,directory):
    def one(item):
        root,objective=item
        r=probe(root,v,objective,deadline)
        r['verification']=replay(r,v,seconds=max(.001,min(120,deadline-time.monotonic())))
        write(directory/f"{root['case']}-{objective}.json",r)
        print(json.dumps({k:r.get(k) for k in ('case','objective','status','hp','last_round','error')}),flush=True)
        return r
    return parallel(one,[(root,o) for root in roots for o in OBJECTIVES])


def searched(roots,records,v,deadline,directory):
    def one(root):
        rows=[r for r in records if r['case']==root['case']];best=max(rows,key=rank)
        executed=probe(root,v,best['objective'],deadline)
        result=dict(case=root['case'],selected_objective=best['objective'],search_seconds=sum(r['seconds'] for r in rows),
            valid_candidates=sum(r['status'] in ('clear','defeat') for r in rows),execution=executed,
            autonomous_match=executed.get('final_hash')==best.get('final_hash') and executed.get('transition_hash')==best.get('transition_hash'))
        write(directory/f"{root['case']}-searched.json",result);return result
    return parallel(one,roots)


def summarize(roots,records,searches,fixed):
    rows=[]
    for root in roots:
        by={r['objective']:r for r in records if r['case']==root['case']}
        search=next(r for r in searches if r['case']==root['case'])
        compact=lambda r:{k:r.get(k) for k in ('status','hp','potions','last_round','power_plays','error')}
        b=by['baseline'];s=search['execution']
        rows.append(dict(case=root['case'],entry_hp=root['hp'],enemies=root['enemies'],arms={k:compact(r) for k,r in by.items()},
            searched=compact(s),selected=search['selected_objective'],search_seconds=search['search_seconds'],
            hp_delta=(s['hp']-b['hp']) if 'hp' in s and 'hp' in b else None,
            fixed_hp_delta=(by[fixed]['hp']-b['hp']) if 'hp' in by[fixed] and 'hp' in b else None))
    def mean(k):
        vals=[r[k] for r in rows if r[k] is not None];return statistics.mean(vals) if len(vals)==len(rows) and vals else None
    return dict(rows=rows,mean_hp_delta=mean('hp_delta'),mean_fixed_hp_delta=mean('fixed_hp_delta'),
        baseline_clears=sum(r['arms']['baseline']['status']=='clear' for r in rows),
        searched_clears=sum(r['searched']['status']=='clear' for r in rows),
        fixed_clears=sum(r['arms'][fixed]['status']=='clear' for r in rows))


def evaluate(v,output):
    plan=json.loads((ROOT/'experiments/E163/plan-v1.json').read_text())
    assert all(plan['manifest'][k]==v[k] for k in ENGINE_KEYS)
    assert list(OBJECTIVES)==plan['objectives']
    start=time.monotonic();deadline=start+1200;directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    discovery=evaluate_roots(plan['discovery'],v,deadline,directory)
    def fixed_rank(o):
        rows=[r for r in discovery if r['objective']==o]
        return (sum(r['status']=='clear' for r in rows),sum(r.get('hp',0) for r in rows),sum(len(r.get('potions',[])) for r in rows))
    fixed=max(OBJECTIVES,key=fixed_rank)
    write(directory/'fixed-selection.json',dict(objective=fixed,rank={o:fixed_rank(o) for o in OBJECTIVES}))
    print(json.dumps(dict(fixed_selected_before_holdout=fixed)),flush=True)
    ds=searched(plan['discovery'],discovery,v,deadline,directory)
    collection=parallel(lambda c:fixture(c,v),plan['holdout']);roots=[]
    write(directory/'holdout-collection.json',collection)
    for r in collection:
        if r['status']!='ready':continue
        pairs=wire_pairs((ROOT/r['trace_path']).parent/'wire.jsonl')
        roots.append(dict(case=r['case'],source=reference(r),commands=len(pairs),prefix_hash=digest([c for c,_ in pairs]),
            entry_hash=r['entry_hash'],reservations=[],previous=r['previous'],hp=r['hp'],enemies=r['enemies']))
    # Freeze generated natural roots before any objective probes on them.
    write(directory/'holdout-roots.json',roots)
    holdout=evaluate_roots(roots,v,deadline,directory);hs=searched(roots,holdout,v,deadline,directory)
    records=discovery+holdout;searches=ds+hs
    result=dict(manifest=v,plan_sha256=file_hash(ROOT/'experiments/E163/plan-v1.json'),selected_fixed=fixed,
        discovery_records=discovery,discovery_search=ds,collection=collection,holdout_roots=roots,
        holdout_records=holdout,holdout_search=hs,discovery=summarize(plan['discovery'],discovery,ds,fixed),
        holdout=summarize(roots,holdout,hs,fixed),full_runs_evaluated=0,model_calls=0,model_cost_usd=0)
    proof=audit(result);result['audit']=proof;result['seconds']=time.monotonic()-start
    fidelity=all(r['status'] in ('clear','defeat') and r['verification']['status']=='match'
        and r['verification']['final_hash']==r['final_hash'] for r in records)
    fidelity&=all(r['recorded_boundary_match'] for r in discovery if r['objective']=='baseline')
    fidelity&=all(r['autonomous_match'] and r['valid_candidates']==4 and r['execution']['status'] in ('clear','defeat') for r in searches)
    no_lost=all(row['searched']['status']=='clear' for group in ('discovery','holdout')
                for row in result[group]['rows'] if row['arms']['baseline']['status']=='clear')
    result['fidelity_pass']=bool(fidelity and proof['pass'])
    result['local_gate']=(result['fidelity_pass'] and len(roots)==6 and no_lost and (result['holdout']['mean_hp_delta'] or 0)>0
        and all(r['search_seconds']<=60 for r in searches) and result['seconds']<=1200)
    result['default_promotion']=False
    print(json.dumps(dict(local_gate=result['local_gate'],fidelity=result['fidelity_pass'],fixed=fixed,
        discovery_delta=result['discovery']['mean_hp_delta'],holdout_delta=result['holdout']['mean_hp_delta'],seconds=result['seconds'])),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','evaluate']);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**manifest(),'experiment':'E163'}
    write(a.output,freeze(v) if a.mode=='freeze' else evaluate(v,a.output))
