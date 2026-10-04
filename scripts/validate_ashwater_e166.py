#!/usr/bin/env python3
"""Three registered same-entry Boss pairs; only optional exhaust polarity differs."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import boundary,finish
from rsi.checkpoints import wire_pairs,file_hash
from rsi.continuation import FrozenProgram
from rsi.engine import Headless
from rsi.research_restore import ENGINE_KEYS
from rsi.run_env import legal_choices,replay
from rsi.selection_semantics import TypedAshwaterProgram
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime

SOURCE=ROOT/'artifacts/runs/e165-evaluation-v1.json'
CASES=[('A0-000',1,17),('A0-000',2,16),('A5-000',1,17)]


def plan(v):
    source=checked(SOURCE)
    assert source['manifest']['code_commit']=='3ac6417a206937ea5a6dc9cc4e970f09522a2277'
    assert all(v[k]==source['manifest'][k] for k in ENGINE_KEYS)
    roots=[]
    for case,act,floor in CASES:
        record=next(r for r in source['records'] if r['case']==case and r['arm']=='astra_campaign')
        wire=ROOT/record['trace_path'];wire=wire.parent/'wire.jsonl'
        assert file_hash(wire)==record['wire.jsonl_sha256']
        pairs=wire_pairs(wire)
        idx=next(i for i,(_,s) in enumerate(pairs) if s.get('decision')=='combat_play'
            and s['context']['act']==act and s['context']['floor']==floor)
        end=next(s for _,s in pairs[idx+1:] if boundary(s))
        roots.append(dict(case=f'{case}-act{act}-floor{floor}',source_case=case,act=act,floor=floor,
            wire=info(wire),prefix_count=idx+1,entry_hash=digest(pairs[idx][1]),
            expected_final_hash=digest(end),expected_status=boundary(end),expected_hp=end['player']['hp']))
    return dict(manifest=v,source=info(SOURCE),roots=roots,arms=['legacy','typed_ashwater'],
        budgets=dict(actions=300,trial_seconds=120,replay_seconds=120,wall_seconds=600),
        scope='Known natural battle entries, not new full runs or held-out win rate')


def trial(root,arm,v,deadline):
    wire=ROOT/root['wire']['path'];assert file_hash(wire)==root['wire']['sha256']
    pairs=wire_pairs(wire);trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),
        {**v,'scope':'E166_known_battle_counterfactual','root':root,'arm':arm})
    r=dict(case=root['case']+'-'+arm,root=root['case'],arm=arm,status='error',steps=0,
        ashwater_selections=[],illegal_actions=0,plan=[])
    engine=None;state={};previous=None;started=time.monotonic()
    program=TypedAshwaterProgram(None) if arm=='typed_ashwater' else FrozenProgram(None)
    def send(command):
        left=min(120-(time.monotonic()-started),deadline-time.monotonic())
        if left<=0:raise TimeoutError('E166 trial/global cap')
        engine.timeout=min(15,left);return engine.send(command)
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs[:root['prefix_count']]):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix divergence {i}')
        assert digest(state)==root['entry_hash']
        r['prefix_commands_verified']=root['prefix_count']
        for step in range(301):
            end=boundary(state)
            if end:r['status']=end;break
            if step==300:raise TimeoutError('E166 action cap')
            choices=legal_choices(state,{})
            chosen,meta=program.choose(state,choices,previous) if len(choices)>1 else (choices[0],{})
            if chosen['action'] not in [c['action'] for c in choices]:
                r['illegal_actions']+=1;raise ValueError('Illegal current action')
            if state['decision']=='card_select' and (program.parent or {}).get('details',{}).get('id')=='ASHWATER':
                r['ashwater_selections'].append(dict(before=digest(state),action=chosen['action'],
                    selected=chosen.get('details'),parent=program.parent['name']))
            trace.write('decision',dict(before=digest(state),state=state,chosen=chosen,**meta))
            before=digest(state);program.remember(state,chosen)
            state=send(chosen['action']);previous=chosen;r['steps']+=1
            r['plan'].append(dict(before=before,action=chosen['action'],after=digest(state)))
        r.update(hp=state['player']['hp'],potions=[p.get('id') for p in state['player']['potions']],
            final_hash=digest(state),transition_hash=digest(r['plan']),
            original_final_match=digest(state)==root['expected_final_hash'])
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started)
    r.pop('plan',None)
    return r


def evaluate(v,path):
    p=checked(path,tracked=True);same_runtime(p,v);checked(ROOT/p['source']['path'],p['source']['sha256'])
    start=time.monotonic();deadline=start+600;records=[];proofs=[]
    for root in p['roots']:
        for arm in p['arms']:
            r=trial(root,arm,v,deadline);records.append(r)
            print(json.dumps({k:r.get(k) for k in ('case','status','hp','error','original_final_match','ashwater_selections')}),flush=True)
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError('E166 replay global cap')
            proofs.append(replay(r,v,seconds=min(120,left)))
    pairs=[]
    for root in p['roots']:
        b,t=[r for r in records if r['root']==root['case']]
        score=lambda r:(int(r['status']=='clear'),r.get('hp',0))
        pairs.append(dict(case=root['case'],baseline=[b['status'],b.get('hp')],treatment=[t['status'],t.get('hp')],
            improved=score(t)>score(b),regressed=score(t)<score(b),transition_equal=b.get('transition_hash')==t.get('transition_hash')))
    raw=audit([records,proofs]);seconds=time.monotonic()-start
    integrity=(all(r['status'] in ('clear','defeat') and not r.get('error') and not r['illegal_actions'] for r in records)
        and all(r['original_final_match'] for r in records if r['arm']=='legacy')
        and all(pf['status']=='match' and pf['final_hash']==r['final_hash'] for r,pf in zip(records,proofs))
        and raw['pass'] and seconds<=600)
    return dict(manifest=v,plan=info(path),records=records,replays=proofs,pairs=pairs,raw_audit=raw,
        integrity_pass=integrity,local_gate=integrity and any(p['improved'] for p in pairs)
            and not any(p['regressed'] for p in pairs) and all(p['transition_equal'] for p in (pairs[0],pairs[2])),
        default_promotion=False,seconds=seconds,model_api_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','evaluate']);parser.add_argument('--plan',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E166'}
    value=plan(v) if args.mode=='plan' else evaluate(v,args.plan)
    write(args.output,value)
    if args.mode=='evaluate':print(json.dumps({k:value[k] for k in ('integrity_pass','local_gate','seconds','pairs','raw_audit')}))
