#!/usr/bin/env python3
"""Recorded acquisition coverage plus one real-engine potion handoff counterfactual."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.acquire_reserve import prepare,confirm
from rsi.battle_search import finish,boundary
from rsi.campaign_teacher import CampaignTeacher,permitted_state,validate
from rsi.checkpoints import file_hash,wire_pairs
from rsi.continuation import FrozenProgram
from rsi.engine import Headless,action
from rsi.research_restore import ENGINE_KEYS
from rsi.run_env import legal_choices,replay
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import manifest,audit,write

RULE=dict(potion_id='VULNERABLE_POTION',until='Boss',release_hp_fraction=.35)


def synthetic():
    counts=dict(accepted=0,rejected=0)
    def rejected(fn):
        try:fn()
        except ValueError:counts['rejected']+=1
        else:raise AssertionError('Invalid acquisition accepted')
    state=dict(decision='shop',context=dict(room_type='Monster'),player=dict(gold=60,hp=60,max_hp=80,
        has_open_potion_slots=True,potions=[dict(index=1,id='VULNERABLE_POTION')]),
        potions=[dict(index=3,id='VULNERABLE_POTION',cost=50,can_buy=True,is_stocked=True)])
    selected=dict(action=action('buy_potion',potion_index=3))
    before=copy.deepcopy(state);intent=prepare(state,selected,RULE)
    after=copy.deepcopy(state);after['player']['gold']=10
    after['player']['potions']=[dict(index=0,id='VULNERABLE_POTION'),dict(index=1,id='VULNERABLE_POTION')]
    rules=confirm(intent,state,selected,after,[]);counts['accepted']+=1
    assert state==before and len(rules)==1
    assert permitted_state(after,rules)[1]==[0,1]
    for room,hp,blocked in [('Monster',60,[0,1]),('Elite',60,[0,1]),('Boss',60,[]),('Monster',28,[])]:
        s=copy.deepcopy(after);s['context']['room_type']=room;s['player']['hp']=hp
        assert permitted_state(s,rules)[1]==blocked;counts['accepted']+=1
    rejected(lambda:confirm(intent,state,selected,state,[]))
    bad=copy.deepcopy(after);bad['player']['gold']=11
    rejected(lambda:confirm(intent,state,selected,bad,[]))
    rejected(lambda:confirm(intent,after,selected,after,[]))
    rejected(lambda:confirm(intent,state,dict(action=action('leave_room')),after,[]))
    rejected(lambda:prepare(state,selected,{**RULE,'potion_id':'FIRE_POTION'}))
    full=copy.deepcopy(state);full['player']['has_open_potion_slots']=False
    rejected(lambda:prepare(full,selected,RULE))
    rejected(lambda:prepare(state,dict(action=action('discard_potion',potion_index=1)),RULE))
    # Synthetic post-discard state: legal fresh acquisition, no pre-discard binding reuse.
    fresh=copy.deepcopy(state);fresh['player']['potions']=[]
    acquired=copy.deepcopy(after);acquired['player']['potions']=[dict(index=0,id='VULNERABLE_POTION')]
    assert confirm(prepare(fresh,selected,RULE),fresh,selected,acquired,[])==[RULE];counts['accepted']+=1
    claim=copy.deepcopy(fresh);claim.update(decision='potion_reward',potion=dict(id='VULNERABLE_POTION'),can_claim=True)
    claim_choice=dict(action=action('claim_potion_reward'))
    assert confirm(prepare(claim,claim_choice,RULE),claim,claim_choice,acquired,[])==[RULE];counts['accepted']+=1
    return counts


def recorded(e):
    report=dict(buys=0,claims=0,historical_packets=0)
    for record in e['records']:
        if record['arm']!='astra_campaign':continue
        assert audit([record])['pass']
        path=ROOT/record['trace_path'];pairs=wire_pairs(path.parent/'wire.jsonl')
        for i,(cmd,after) in enumerate(pairs):
            if cmd.get('action') not in ('buy_potion','claim_potion_reward'):continue
            state=pairs[i-1][1];choice=dict(action=cmd)
            if cmd['action']=='buy_potion':
                offer=next(p for p in state['potions'] if p['index']==cmd['args']['potion_index']);report['buys']+=1
            else:offer=state['potion'];report['claims']+=1
            rule={**RULE,'potion_id':offer['id']}
            assert confirm(prepare(state,choice,rule),state,choice,after,[])==[rule]
        requests={}
        for line in path.read_text().splitlines():
            event=json.loads(line);d=event['data']
            if event['kind']=='campaign_request':requests[d['seq']]=d
            if event['kind']=='campaign_response':
                c=validate(d['packet'],requests[d['seq']]);assert c['action']==d['choice'];report['historical_packets']+=1
    assert report==dict(buys=9,claims=22,historical_packets=200)
    return report


def trial(source,v,arm):
    path=ROOT/source['trace_path'];events=[json.loads(l) for l in path.read_text().splitlines()]
    req=next(e['data'] for e in events if e['kind']=='campaign_request' and e['data']['seq']==30)
    packet=json.loads((ROOT/req['response_path']).read_text());choices=req['choices']
    selected=next(c for c in choices if c['id']==packet['choice_id'])
    pairs=wire_pairs(path.parent/'wire.jsonl');buy=next(i for i in range(1,len(pairs))
        if digest(pairs[i-1][1])==req['state_hash'] and pairs[i][0]==selected['action'])
    battle=next(i for i in range(buy+1,len(pairs)) if pairs[i][1].get('decision')=='combat_play')
    expected_end=next(s for _,s in pairs[battle+1:] if boundary(s))
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'E162_handoff_counterfactual','arm':arm})
    r=dict(case=arm,status='error',steps=0,run_id=trace.directory.name,emergency_releases=0,blocked_decisions=0)
    engine=None;started=time.monotonic();state={}
    teacher=CampaignTeacher(trace,arm,None,None,0,experiment='E162',acquire_reservation=True)
    teacher.reservations=packet['potion_reservations'];program=FrozenProgram(None);previous=None
    def send(c):
        left=120-(time.monotonic()-started)
        if left<=0:raise TimeoutError('Handoff trial cap')
        engine.timeout=min(15,left);return engine.send(c)
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs[:battle+1]):
            before=state
            if i==buy and arm=='acquire_reserve':teacher.acquisition=prepare(state,selected,RULE)
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch {i}')
            if i==buy:teacher.accepted(before,selected,state)
        r['prefix_commands_verified']=battle+1;r['entry_hash']=digest(state)
        for step in range(301):
            end=boundary(state)
            if end:r['status']=end;break
            if step==300:raise TimeoutError('Handoff action cap')
            masked,blocked=permitted_state(state,teacher.reservations);r['blocked_decisions']+=bool(blocked)
            choices=legal_choices(state,{})
            chosen,_=program.choose(masked,choices,previous) if len(choices)>1 else (choices[0],{})
            assert chosen['action'] in [c['action'] for c in choices]
            cmd=chosen['action']
            if cmd['action']=='use_potion':
                idx=cmd['args']['potion_index'];assert idx not in blocked
                potion=next(p for p in state['player']['potions'] if p['index']==idx)
                if arm=='acquire_reserve' and potion['id']==RULE['potion_id']:
                    assert state['player']['hp']/state['player']['max_hp']<=.35
                    r['emergency_releases']+=1
            trace.write('decision',dict(state=state,chosen=chosen,blocked=blocked))
            program.remember(state,chosen);previous=chosen;state=send(cmd);r['steps']+=1
        r.update(final_hash=digest(state),hp=state['player']['hp'],potions=[p['id'] for p in state['player']['potions']],
                 extra_expert_calls=teacher.count,reservations=teacher.reservations)
        r['baseline_boundary_match']=digest(state)==digest(expected_end) if arm=='baseline' else None
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started);return r


def main(output):
    if output.exists():raise ValueError('Never overwrite evidence')
    started=time.monotonic();v={**manifest(),'experiment':'E162'}
    e=json.loads((ROOT/'experiments/E160/evaluation-v1.json').read_text())
    assert all(v[k]==e['manifest'][k] for k in ENGINE_KEYS)
    checks=synthetic();old=recorded(e)
    source=next(r for r in e['records'] if r['case']=='A0-000' and r['arm']=='astra_campaign')
    records=[trial(source,v,arm) for arm in ('baseline','acquire_reserve')]
    proofs=[replay(r,v,seconds=120) for r in records]
    b,t=records
    result=dict(manifest=v,source_sha256=file_hash(ROOT/'experiments/E160/evaluation-v1.json'),synthetic=checks,
        recorded=old,records=records,replays=proofs,scope='Compatibility/handoff only; one known counterfactual, not win rate')
    result['audit']=audit([records,proofs]);result['seconds']=time.monotonic()-started
    result['passed']=(all(r['status'] in ('clear','defeat') and r['extra_expert_calls']==0 for r in records)
        and b['baseline_boundary_match'] and (RULE['potion_id'] in t['potions'] or t['emergency_releases']>0)
        and all(p['status']=='match' and p['final_hash']==r['final_hash'] for p,r in zip(proofs,records))
        and result['audit']['pass'] and result['seconds']<=600)
    write(output,result);print(json.dumps({k:result[k] for k in ('passed','synthetic','recorded','seconds','audit')}))
    print(json.dumps([{k:r.get(k) for k in ('case','status','hp','potions','error','baseline_boundary_match','emergency_releases')} for r in records]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
