"""E113 preregistered natural-prefix, paired multi-seed backend audition."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import uuid

from rsi.decider_backend import Backend, BackendStopped, Ledger, JEV, DEEPSEEK
from rsi.engine import ROOT, CHARACTERS, Headless
from rsi.full import STRATEGY, macro_candidates, fixed_macro
from rsi.numerical import intent_damage
from rsi.planner import choose_plan
from rsi.policy import combat_candidates, model_state
from rsi.potions import with_potions
from rsi.resources import require_resource_interface
from rsi.teacher import terminal
from rsi.trace import Trace, digest, version_manifest

D = ROOT / 'experiments/E113'
ARMS = ['program','jev','deepseek']


def manifest():
    m = version_manifest()
    if m['tracked_dirty']: raise RuntimeError('Commit code/fixtures before evaluation')
    if m['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise RuntimeError('Wrong pinned game')
    return m


def position(state):
    c = state.get('context') or {}
    return state.get('act', c.get('act', 1)), state.get('floor', c.get('floor', 0))


def choices_for(state, history):
    if state['decision'] == 'combat_play': return with_potions(state, combat_candidates(state))
    return macro_candidates(state, history, resource_decisions=True)


def program(state, choices):
    if state['decision'] == 'combat_play':
        return choose_plan(state, [c for c in choices if c['action']['action'] != 'use_potion'],
                           triggers=True, retaliation=True)[0]
    if state['decision'] == 'potion_reward':
        name = 'claim_potion_reward' if state.get('can_claim') else 'skip_potion_reward'
        return next(c for c in choices if c['action']['action'] == name)
    regular = [c for c in choices if c['action']['action'] not in ('use_potion','discard_potion')]
    return fixed_macro(state, regular)


def update_history(history, before, choice):
    if before['decision'] == 'map_select': history['removed_here'] = False
    if choice['action']['action'] == 'remove_card': history['removed_here'] = True
    if before['decision'] != 'card_select': history['previous'] = {'scene':before['decision'],'choice':choice}


def boundary(state):
    # Existing audited terminal classifier excludes potion-generated card rewards.
    answer = terminal(state)
    return {'boss_clear':'win','boss_defeat':'defeat'}.get(answer)


def new_trace(m, **extra):
    return Trace(ROOT/'artifacts/runs'/('e113-'+str(uuid.uuid4())), {**m,'experiment':'E113',**extra})


def finish(trace, result, engine, state, started):
    if engine:
        engine.close()
        stderr = (trace.directory/'engine.stderr.log').read_bytes()
        result['stderr_sha256'] = hashlib.sha256(stderr).hexdigest()
        result['wire_sha256'] = hashlib.sha256((trace.directory/'wire.jsonl').read_bytes()).hexdigest()
        if b'forcing game_over' in stderr:
            result.update(status='engine_error',error='upstream forced game_over after deadlock')
    p = state.get('player',{})
    result.update(final_hp=p.get('hp'),final_max_hp=p.get('max_hp'),final_position=position(state),
                  final_round=state.get('round'),final_state_hash=digest(state),
                  final_potions=[x.get('id',x.get('name')) for x in p.get('potions',[])],
                  seconds=round(time.monotonic()-started,3))
    trace.write('summary',result)
    result['trace_path'] = str(trace.path.relative_to(ROOT)); result['trace_sha256'] = trace.close()
    (trace.directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def freeze_source(config, m):
    trace = new_trace(m,phase='freeze',config=config); engine=None; state={}; start=time.monotonic()
    out={**config,'status':'error','steps':0}; commands=[]; latest=None; reward=None; seen=set(); history={}; selected_reward=None
    try:
        engine=Headless(trace.directory, resource_decisions=True)
        cmd={'cmd':'start_run', **{k:config[k] for k in ('character','seed','ascension')}}
        state=engine.send(cmd); commands.append(cmd); require_resource_interface(state)
        for step in range(501):
            act,floor=position(state)
            if state.get('decision')=='game_over': out['status']='source_defeat';break
            if act!=1 or floor>=10: out['status']='boundary';break
            if step==500 or time.monotonic()-start>90: out['status']='source_budget';break
            key=(act,floor)
            if state['decision']=='combat_play' and key not in seen:
                seen.add(key)
                latest={'entry_hash':digest(state),'commands':list(commands),'entry':state,'history':dict(history)}
                selected_reward=reward
            if state['decision']=='card_reward' and not state.get('from_event') and 'gold_earned' in state:
                reward={'entry_hash':digest(state),'commands':list(commands),'entry':state,'history':dict(history)}
            choices=choices_for(state,history); choice=program(state,choices)
            trace.write('before',{'state':state,'state_hash':digest(state)})
            trace.write('selected',choice);update_history(history,state,choice)
            state=engine.send(choice['action']);commands.append(choice['action']);out['steps']=step+1
            trace.write('after',{'state':state,'state_hash':digest(state)})
        out['combat_entries_seen']=len(seen)
    except Exception as exc:
        out.update(status='engine_error',error=f'{type(exc).__name__}: {exc}');trace.write('failure',out['error'])
    out=finish(trace,out,engine,state,start)
    return {'id':config['id'],'config':config,'source':out,'combat':latest,'reward':selected_reward}


def freeze(m):
    configs=[{'id':f'{i:03}-{c.lower()}','seed':f'e113_audition_20260929_{i:03}',
              'character':c,'ascension':10,'cohort':'pilot' if i<=2 else 'confirm'}
             for i in range(1,7) for c in CHARACTERS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        cases=list(pool.map(lambda c:freeze_source(c,m), configs))
    (D/'fixtures.json').write_text(json.dumps({'manifest':m,'cases':cases},indent=2)+'\n')
    print(json.dumps({'sources':dict(Counter(c['source']['status'] for c in cases)),
                      'combat':sum(bool(c['combat']) for c in cases),'reward':sum(bool(c['reward']) for c in cases)}),flush=True)


def payload(state, recent, history):
    return {'state':model_state(state),'strategy':STRATEGY,'recent_actions':recent[-6:],
            'previous_decision':history.get('previous'),
            'computed':{'current_visible_incoming_before_new_plays':sum(intent_damage(e) for e in state.get('enemies',[])),
                        'limitation':'Not a simulation: killing, weakness, block, retaliation and powers change damage.'}}


def continuation(case, task, arm, backend, m, deadline):
    base={'case':case['id'],'character':case['config']['character'],'seed':case['config']['seed'],
          'cohort':case['config']['cohort'],'task':task,'arm':arm,'status':'error','steps':0,'battles_completed':0}
    fixture=case[task]
    if fixture is None: return {**base,'status':'missing_fixture'}
    if time.monotonic()>=deadline: return {**base,'status':'budget_censored'}
    if backend and backend.ledger.snapshot()['stop_reason']: return {**base,'status':'backend_censored','reason':backend.ledger.snapshot()['stop_reason']}
    trace=new_trace(m,**base);start=time.monotonic();engine=None;state={};history=dict(fixture['history']);recent=[]
    active_battle=None;seen_hashes=Counter();used_potions=[]
    try:
        engine=Headless(trace.directory,resource_decisions=True)
        for cmd in fixture['commands']:
            if time.monotonic()>=deadline: raise BackendStopped('global time budget')
            state=engine.send(cmd)
        base['entry_verified']=digest(state)==fixture['entry_hash']
        if not base['entry_verified']: raise RuntimeError('Frozen entry mismatch')
        base['entry_hp']=state['player']['hp'];base['entry_position']=position(state)
        trace.write('entry',{'state':state,'state_hash':digest(state)})
        limit=240 if task=='combat' else 300; seconds=900 if task=='combat' else 180
        for step in range(limit+1):
            if task=='combat':
                status=boundary(state)
                if status: base['status']=status;break
            else:
                if state['decision']=='game_over':base['status']='defeat';break
                if state['decision']=='combat_play':active_battle=position(state)
                elif active_battle and boundary(state)=='win':
                    base['battles_completed']+=1;active_battle=None
                if base['battles_completed']>=2 or position(state)[0]!=1 or position(state)[1]>=10:
                    base['status']='survived';break
            if step==limit or time.monotonic()-start>seconds or time.monotonic()>=deadline:
                base['status']='budget_exhausted';break
            h=digest(state);seen_hashes[h]+=1
            if seen_hashes[h]>5: raise RuntimeError('Repeated unchanged decision')
            choices=choices_for(state,history)
            # Reward audition concerns a card or skip, not consuming an AnyTime potion.
            if task=='reward' and step==0:
                choices=[c for c in choices if c['action']['action'] in ('select_card_reward','skip_card_reward')]
            trace.write('before',{'state':state,'state_hash':h});trace.write('candidates',choices)
            decision_backend=backend if task=='combat' or step==0 else None
            if len(choices)==1: choice=choices[0];source='only_choice'
            elif decision_backend: choice=decision_backend.choose(payload(state,recent,history),choices,trace);source=arm
            else: choice=program(state,choices);source='program'
            if choice not in choices: raise RuntimeError('Illegal selected choice')
            trace.write('selected',{'choice':choice,'source':source})
            if step==0:base['first_choice']=choice
            if choice['action']['action']=='use_potion':used_potions.append(choice.get('name'))
            update_history(history,state,choice);recent.append({'round':state.get('round'),'choice':choice})
            state=engine.send(choice['action']);base['steps']=step+1
            trace.write('after',{'state':state,'state_hash':digest(state)})
    except BackendStopped as exc:
        base.update(status='backend_censored',error=str(exc));trace.write('failure',str(exc))
    except Exception as exc:
        base.update(status='error',error=f'{type(exc).__name__}: {exc}');trace.write('failure',base['error'])
    base['potions_used']=used_potions
    result=finish(trace,base,engine,state,start)
    rows=[json.loads(x) for x in (ROOT/result['trace_path']).read_text().splitlines()]
    responses=[r['data'] for r in rows if r['kind']=='model_response']
    result.update(model_calls=sum(r['kind']=='model_request' for r in rows),
                  model_failures=sum(r['kind']=='model_failure' for r in rows),
                  cost_usd=sum(r['response'].get('usage',{}).get('cost') or 0 for r in responses),
                  api_seconds=[round(r['seconds'],3) for r in responses],
                  usage=[r['response'].get('usage',{}) for r in responses],
                  models=sorted({str(r['response'].get('model')) for r in responses}),
                  providers=sorted({str(r['response'].get('provider')) for r in responses}))
    (trace.directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def paired(a,b,task):
    valid={'win','defeat'} if task=='combat' else {'survived','defeat'}
    if a['status'] not in valid or b['status'] not in valid: return 'invalid'
    av=a['status']!='defeat';bv=b['status']!='defeat'
    if av!=bv:return 'better' if bv else 'worse'
    if task=='reward' and a['battles_completed']!=b['battles_completed']:
        return 'better' if b['battles_completed']>a['battles_completed'] else 'worse'
    delta=(b['final_hp'] or 0)-(a['final_hp'] or 0)
    return 'better' if delta>=3 else 'worse' if delta<=-3 else 'tie'


def summarize(results):
    summary={};index={(r['case'],r['task'],r['arm']):r for r in results}
    for cohort in ['pilot','confirm']:
        for task in ['combat','reward']:
            for arm in ARMS:
                rs=[r for r in results if (r['cohort'],r['task'],r['arm'])==(cohort,task,arm)]
                lat=sorted(x for r in rs for x in r.get('api_seconds',[]))
                valid=[r for r in rs if r['status'] in ('win','defeat','survived')]
                comparisons={}
                for ref in ['program','jev']:
                    if ref==arm:continue
                    pairs=[(index[(r['case'],task,ref)],r) for r in rs if (r['case'],task,ref) in index]
                    counts=Counter(paired(a,b,task) for a,b in pairs)
                    deltas=[(b['final_hp'] or 0)-(a['final_hp'] or 0) for a,b in pairs if paired(a,b,task)!='invalid']
                    comparisons[ref]={'pairs':dict(counts),'median_hp_delta':statistics.median(deltas) if deltas else None,
                        'baseline_wins':sum(a['status']=='win' for a,b in pairs),'treatment_wins':sum(b['status']=='win' for a,b in pairs)}
                summary[f'{cohort}/{task}/{arm}']={'n':len(rs),'statuses':dict(Counter(r['status'] for r in rs)),
                    'calls':sum(r.get('model_calls',0) for r in rs),'cost_usd':sum(r.get('cost_usd',0) for r in rs),
                    'p50_seconds':statistics.median(lat) if lat else None,
                    'p95_seconds':lat[max(0,math.ceil(.95*len(lat))-1)] if lat else None,
                    'mean_cost_per_completed':sum(r.get('cost_usd',0) for r in rs)/len(valid) if valid else None,
                    'comparisons':comparisons}
    return summary


def evaluate(m):
    fixtures=json.loads((D/'fixtures.json').read_text());cases=fixtures['cases']
    ledgers={'jev':Ledger(1000,1.),'deepseek':Ledger(1000,4.)}
    backends={'program':None,'jev':Backend(JEV,ledgers['jev']),'deepseek':Backend(DEEPSEEK,ledgers['deepseek'])}
    started=time.monotonic();deadline=started+3600;results=[]
    output={'experiment':'E113','manifest':m,'fixtures_sha256':hashlib.sha256((D/'fixtures.json').read_bytes()).hexdigest()}
    for cohort in ['pilot','confirm']:
        jobs=[(c,t,a) for c in cases if c['config']['cohort']==cohort for t in ['combat','reward'] for a in ARMS]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(continuation,c,t,a,backends[a],m,deadline):(c['id'],t,a) for c,t,a in jobs}
            for f in as_completed(futures):
                r=f.result();results.append(r)
                print(json.dumps({k:r.get(k) for k in ['case','task','arm','status','final_hp','model_calls','cost_usd','error']}),flush=True)
                output.update(results=results,ledgers={k:v.snapshot() for k,v in ledgers.items()},summary=summarize(results),seconds=round(time.monotonic()-started,3))
                (ROOT/'artifacts/runs/e113-progress.json').write_text(json.dumps(output,indent=2)+'\n')
        # Interface errors are distinct from model API failures. Do not promote a broken harness.
        invalid=sum(r.get('entry_verified') is False or r['status']=='engine_error' for r in results)
        if invalid>len(results)*.1:
            output['evaluation_stop']='more than 10% replay/engine errors';break
    (D/'results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'done':True,'ledgers':output['ledgers'],'summary':output['summary']}),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['freeze','evaluate']);a=ap.parse_args()
    m=manifest()
    if a.phase=='freeze':freeze(m)
    else:evaluate(m)

if __name__=='__main__': main()
