#!/usr/bin/env python3
"""Exact subset domains and one independently replayed natural Pael continuation."""
import argparse
import itertools
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import finish
from rsi.campaign_teacher import validate
from rsi.checkpoints import file_hash, wire_pairs
from rsi.engine import Headless, first_action
from rsi.ppo_actions import complete_choices
from rsi.research_restore import ENGINE_KEYS
from rsi.run_env import replay
from rsi.subset_action import contract, resolve, validate_fresh
from rsi.trace import Trace, digest
from scripts.evaluate_battle_search_e120 import manifest, audit, write


def synthetic():
    domains=valid=invalid=0
    def rejected(fn):
        nonlocal invalid
        try:fn()
        except ValueError:invalid+=1
        else:raise AssertionError('Invalid subset accepted')
    for n in range(9):
        for lo in range(n+1):
            for hi in range(lo,n+1):
                state=dict(decision='card_select', cards=[dict(index=2*i+1) for i in range(n)],min_select=lo,max_select=hi)
                domain=contract(state);domains+=1;actual=set()
                for k in range(n+1):
                    for subset in itertools.combinations(domain['indexes'],k):
                        if lo<=k<=hi:
                            c=resolve(domain,list(reversed(subset)),digest(state));validate_fresh(state,c)
                            actual.add(digest(c['action']));valid+=1
                        else:rejected(lambda:resolve(domain,list(subset),digest(state)))
                assert actual=={digest(c['action']) for c in complete_choices(state)}
                for bad in ([999],[True],[1.0],['1'],[1,1],None):
                    rejected(lambda:resolve(domain,bad,digest(state)))
                rejected(lambda:resolve(domain,domain['indexes'][:lo],'stale'))
    state=dict(decision='card_select',cards=[dict(index=i) for i in range(18)],min_select=5,max_select=5)
    domain=contract(state);count=0
    for subset in itertools.combinations(range(18),5):
        resolve(domain,list(subset),digest(state));count+=1
    assert count==8568==domain['legal_subsets']
    request=dict(case='synthetic',run_id='test',seq=1,state_hash=digest(state),state=state,choices=[],selection_contract=domain)
    packet={k:request[k] for k in ('case','run_id','seq','state_hash')}
    packet.update(choice_id='subset',selected_indices=[4,3,2,1,0],campaign_plan='Compatibility probe.',potion_reservations=[])
    validate_fresh(state,validate(packet,request))
    rejected(lambda:validate({**packet,'state_hash':'stale'},request))
    rejected(lambda:validate({**packet,'choice_id':'a000'},request))
    rejected(lambda:validate({**packet,'selected_indices':[1,1,2,3,4]},request))
    return dict(domains=domains,valid_small_subsets=valid,invalid_rejected=invalid,large_valid_subsets=count,passed=True)


def continuation(source,v):
    assert audit([source])['pass']
    pairs=wire_pairs((ROOT/source['trace_path']).parent/'wire.jsonl')
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'E161_compatibility_continuation'})
    started=time.monotonic();engine=None;state={};r=dict(case='Pael-A5-001',status='error',steps=0,run_id=trace.directory.name)
    def send(command):
        left=120-(time.monotonic()-started)
        if left<=0:raise TimeoutError('Continuation cap')
        engine.timeout=min(15,left)
        return engine.send(command)
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch at {i}')
        r['prefix_commands_verified']=len(pairs)
        domain=contract(state);assert domain['legal_subsets']==8568
        r['entry_hash']=digest(state);before=state['player']['deck_size']
        selected=resolve(domain,[0,1,2,3,4],digest(state));validate_fresh(state,selected)
        trace.write('decision',dict(state=state,selection_contract=domain,chosen=selected))
        state=send(selected['action']);r['steps']=1
        r['removed_cards']=before-state['player']['deck_size'];assert r['removed_cards']==5
        for _ in range(10):
            if state['decision']=='map_select' and state['player']['hp']>0:
                r['status']='map_reached';break
            if state['decision'] in ('combat_play','game_over'):raise ValueError('Unexpected continuation boundary')
            command=first_action(state);trace.write('continuation',dict(state=state,command=command))
            state=send(command);r['steps']+=1
        r['final_hash']=digest(state);r['final_decision']=state.get('decision')
        r['domain_bytes']=len(json.dumps(domain));r['represented_subsets']=domain['legal_subsets']
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started)
    return r


def main(output):
    if output.exists():raise ValueError('Never overwrite evidence')
    started=time.monotonic();v={**manifest(),'experiment':'E161'}
    e=json.loads((ROOT/'experiments/E160/evaluation-v1.json').read_text())
    assert all(v[k]==e['manifest'][k] for k in ENGINE_KEYS)
    s=synthetic()
    source=next(r for r in e['records'] if r['case']=='A5-001' and r['arm']=='astra_campaign')
    r=continuation(source,v);proof=replay(r,v,seconds=120)
    result=dict(manifest=v,source_sha256=file_hash(ROOT/'experiments/E160/evaluation-v1.json'),
        scope='Compatibility only; E160 outcome unchanged',synthetic=s,continuation=r,verification=proof)
    result['audit']=audit([r,proof]);result['seconds']=time.monotonic()-started
    result['passed']=(s['passed'] and r['status']=='map_reached' and proof['status']=='match'
                      and proof['final_hash']==r['final_hash'] and result['audit']['pass'] and result['seconds']<=300)
    write(output,result);print(json.dumps({k:result[k] for k in ('passed','synthetic','seconds','audit')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
