#!/usr/bin/env python3
"""Four independently frozen potion arms on 18 natural encounter entries."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import boundary,finish,CONTROL
from rsi.campaign_teacher import permitted_state
from rsi.checkpoints import wire_pairs,file_hash
from rsi.engine import Headless
from rsi.potion_applicability import defer_reason
from rsi.potion_program import PotionProgram
from rsi.research_restore import ENGINE_KEYS
from rsi.run_env import legal_choices,replay
from rsi.teacher import select
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime

ARMS={'legacy':(False,False),'typed':(False,True),'applicable':(True,False),'combined':(True,True)}


def plan(v):
    roots=[];use_states=[];sources=[]
    for experiment,path in [('E160',ROOT/'experiments/E160/evaluation-v1.json'),('E165',ROOT/'artifacts/runs/e165-evaluation-v1.json')]:
        source=checked(path);sources.append(info(path));assert all(v[k]==source['manifest'][k] for k in ENGINE_KEYS)
        for record in source['records']:
            if record['arm']!='astra_campaign':continue
            trace=ROOT/record['trace_path'];wire=trace.parent/'wire.jsonl'
            assert file_hash(wire)==record['wire.jsonl_sha256']
            assert file_hash(trace)==record['trace_sha256']
            pairs=wire_pairs(wire);seen=set();reservations=[];previous=None
            for line in trace.read_text().splitlines():
                event=json.loads(line);d=event['data']
                if event['kind']=='campaign_response':reservations=d['packet']['potion_reservations']
                if event['kind']=='acquisition_confirmed':reservations=d['reservations']
                if event['kind']!='decision':continue
                state=d['state'];ctx=state.get('context') or {};key=(ctx.get('act'),ctx.get('floor'))
                if experiment=='E165' and d['chosen']['action']['action']=='use_potion':
                    use_states.append(dict(source=info(trace),state_hash=digest(state),action=d['chosen']['action'],
                        potion=d['chosen']['details'],reservations=reservations))
                if state['decision']=='combat_play' and key not in seen:
                    seen.add(key)
                    wanted=(key[0]==2 or (key[0]==1 and ctx.get('room_type')=='Boss')) if experiment=='E160' else ctx.get('room_type')=='Boss'
                    if wanted:
                        idx=next(i for i,(_,s) in enumerate(pairs) if digest(s)==digest(state))
                        end=next(s for _,s in pairs[idx+1:] if boundary(s))
                        roots.append(dict(case=f'{experiment}-{record["case"]}-act{key[0]}-floor{key[1]}',
                            seed=record['seed'],wire=info(wire),prefix_count=idx+1,entry_hash=digest(state),
                            expected_final_hash=digest(end),expected_status=boundary(end),expected_hp=end['player']['hp'],
                            reservations=reservations,previous=previous,context=ctx,
                            enemies=[e['name'] for e in state['enemies']],entry_hp=state['player']['hp']))
                previous=d['chosen']
    assert len(roots)==18
    return dict(manifest=v,sources=sources,roots=roots,e165_potion_states=use_states,arms=ARMS,
        budgets=dict(actions=300,trial_seconds=120,replay_seconds=120,wall_seconds=900,workers=4),
        gate='Fidelity; no HP regression or lost clear; >=2 source seeds have HP/count Pareto improvements. Compare applicable/legacy and combined/typed separately. Known roots only, no default promotion.',
        limitations='Visible intents only; regen checks a present deficit, not certified future healing; Ashwater/Snecko abstain without a verified transformation model. Other potions retain baseline behavior.')


def trial(root,arm,v,deadline):
    assert info(ROOT/root['wire']['path'])==root['wire'];pairs=wire_pairs(ROOT/root['wire']['path'])
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'E168_known_entry_factorial','root':root,'arm':arm})
    r=dict(case=root['case']+'-'+arm,root=root['case'],seed=root['seed'],arm=arm,status='error',steps=0,
        potion_uses=[],deferred=Counter(),illegal_actions=0,reservation_violations=0)
    engine=None;state={};previous=root['previous'];trans=[];started=time.monotonic()
    program=PotionProgram(previous,*ARMS[arm])
    def send(c):
        left=min(120-(time.monotonic()-started),deadline-time.monotonic())
        if left<=0:raise TimeoutError('E168 trial/global cap')
        engine.timeout=min(15,left);return engine.send(c)
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs[:root['prefix_count']]):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch {i}')
        assert digest(state)==root['entry_hash'];r['prefix_commands_verified']=root['prefix_count']
        for step in range(301):
            end=boundary(state)
            if end:r['status']=end;break
            if step==300:raise TimeoutError('E168 action cap')
            choices=legal_choices(state,{})
            masked,blocked=permitted_state(state,root['reservations'])
            chosen,meta=program.choose(masked,choices,previous) if len(choices)>1 else (choices[0],{})
            if chosen['action'] not in [c['action'] for c in choices]:
                r['illegal_actions']+=1;raise ValueError('Illegal choice')
            if chosen['action']['action']=='use_potion':
                if chosen['action']['args']['potion_index'] in blocked:
                    r['reservation_violations']+=1;raise ValueError('Reservation violated')
                r['potion_uses'].append(dict(state_hash=digest(state),round=state.get('round'),
                    potion_id=chosen['details']['id'],action=chosen['action']))
            r['deferred'].update(x['reason'] for x in meta.get('potion_applicability',[]) if x['reason'])
            trace.write('decision',dict(before=digest(state),state=state,chosen=chosen,reserved=blocked,**meta))
            before=digest(state);program.remember(state,chosen);state=send(chosen['action']);previous=chosen;r['steps']+=1
            trans.append(dict(before=before,action=chosen['action'],after=digest(state)))
        r.update(hp=state['player']['hp'],potions=[p['id'] for p in state['player']['potions']],
            final_hash=digest(state),transition_hash=digest(trans),original_final_match=digest(state)==root['expected_final_hash'])
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started);return r


def compare(roots,records,b,t):
    rows=[]
    for root in roots:
        base=next(r for r in records if r['root']==root['case'] and r['arm']==b)
        test=next(r for r in records if r['root']==root['case'] and r['arm']==t)
        hp=test.get('hp',0)-base.get('hp',0);potions=len(test.get('potions',[]))-len(base.get('potions',[]))
        lost=base['status']=='clear' and test['status']!='clear'
        rows.append(dict(case=root['case'],seed=root['seed'],baseline=[base['status'],base.get('hp'),base.get('potions')],
            treatment=[test['status'],test.get('hp'),test.get('potions')],hp_delta=hp,potion_count_delta=potions,
            lost_clear=lost,pareto_improved=not lost and test['status']=='clear' and hp>=0 and potions>=0 and (hp>0 or potions>0),
            transition_equal=base.get('transition_hash')==test.get('transition_hash')))
    seeds=sorted({r['seed'] for r in rows if r['pareto_improved']})
    return dict(baseline=b,treatment=t,rows=rows,improved_seeds=seeds,
        total_hp_delta=sum(r['hp_delta'] for r in rows),total_potion_count_delta=sum(r['potion_count_delta'] for r in rows),
        outcome_gate=len(seeds)>=2 and not any(r['lost_clear'] or r['hp_delta']<0 for r in rows))


def evaluate(v,path,output):
    p=checked(path,tracked=True);same_runtime(p,v);assert p['arms']=={k:list(x) for k,x in ARMS.items()}
    for source in p['sources']:checked(ROOT/source['path'],source['sha256'])
    started=time.monotonic();deadline=started+900;directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    diagnosis=[]
    for use in p['e165_potion_states']:
        file=ROOT/use['source']['path'];assert info(file)==use['source']
        state=next(e['data']['state'] for e in map(json.loads,file.read_text().splitlines())
            if e['kind']=='decision' and digest(e['data']['state'])==use['state_hash'])
        planned=select(state,{**CONTROL,'potions':'none'})[0]['action']
        diagnosis.append(dict(state_hash=use['state_hash'],potion_id=use['potion']['id'],
            round=state.get('round'),context=state['context'],defer_reason=defer_reason(state,use['potion'],planned)))
    def one(item):
        root,arm=item;r=trial(root,arm,v,deadline)
        r['verification']=replay(r,v,seconds=max(.001,min(120,deadline-time.monotonic())))
        write(directory/(r['case']+'.json'),r)
        print(json.dumps({k:r.get(k) for k in ('case','status','hp','potions','error','original_final_match')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(one,[(root,arm) for root in p['roots'] for arm in ARMS]))
    proof=audit(records);seconds=time.monotonic()-started
    integrity=(all(r['status'] in ('clear','defeat') and not r.get('error') and r['illegal_actions']==0
        and r['reservation_violations']==0 and r['verification']['status']=='match'
        and r['verification']['final_hash']==r['final_hash'] for r in records)
        and all(r['original_final_match'] for r in records if r['arm']=='legacy') and proof['pass'] and seconds<=900)
    comparisons=[compare(p['roots'],records,b,t) for b,t in [('legacy','typed'),('legacy','applicable'),('typed','combined')]]
    return dict(manifest=v,plan=info(path),records=records,diagnosis=diagnosis,comparisons=comparisons,raw_audit=proof,
        integrity_pass=integrity,local_gate=integrity and comparisons[-1]['outcome_gate'],default_promotion=False,
        seconds=seconds,model_api_calls=0,full_runs_evaluated=0)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['plan','evaluate']);ap.add_argument('--plan',type=Path)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E168'}
    value=plan(v) if a.mode=='plan' else evaluate(v,a.plan,a.output)
    write(a.output,value)
    if a.mode=='evaluate':print(json.dumps({k:value[k] for k in ('integrity_pass','local_gate','seconds','raw_audit')}))
