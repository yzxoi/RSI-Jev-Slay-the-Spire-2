#!/usr/bin/env python3
"""Exhaust all 32 subsets at five registered natural opening states."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import boundary,finish
from rsi.checkpoints import wire_pairs
from rsi.continuation import FrozenProgram
from rsi.engine import Headless
from rsi.opening_subset import opening_domain,indexes,candidate_id,rank,pick
from rsi.run_env import legal_choices,replay
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime

SOURCES=[('21526f07-71b7-47c0-912c-14217e63bc89',n) for n in (124,148,172,196)]+[
    ('cd9a5cb9-82d9-430e-ba29-05debd6f7974',306)]


def plan(v):
    source_path=ROOT/'experiments/E167/plan-v1.json';source=checked(source_path,tracked=True)
    certificate_path=ROOT/'experiments/E167/evaluation-v1.json';certificate=checked(certificate_path,tracked=True)
    roots=[]
    for run,n in SOURCES:
        ref=next(s for s in source['sources'] if s['record']['run_id']==run)
        wire=ROOT/ref['wire']['path'];assert info(wire)==ref['wire'];pairs=wire_pairs(wire)
        cmd,state=pairs[n-1];before=next(s for _,s in reversed(pairs[:n-1]) if s.get('decision'))
        domain=opening_domain(state,cmd,before);choices=legal_choices(state,{})
        assert len(choices)==domain['legal_subsets']==32
        trace=ROOT/ref['record']['trace_path'];assert info(trace)['sha256']==ref['record']['trace_sha256']
        events=[json.loads(x) for x in trace.read_text().splitlines()]
        parent=next(e['data']['chosen'] for e in events if e['kind']=='decision'
                    and e['data']['chosen']['action']==cmd and digest(e['data']['state'])==digest(before))
        program=FrozenProgram(parent);baseline=program.choose(state,choices,parent)[0]
        if run==SOURCES[-1][0]:
            natural=certificate['continuation'];end_hash=natural['final_hash'];end_status=natural['status'];end_hp=natural['hp']
        else:
            assert pairs[n][0]==baseline['action']
            end=next(s for _,s in pairs[n:] if boundary(s))
            end_hash=digest(end);end_status=boundary(end);end_hp=end['player']['hp']
        status_indices=[c['index'] for c in state['cards'] if c['type'] in ('Status','Curse')]
        roots.append(dict(case=f'opening-{run[:8]}-{n}',source_run=run,seed=ref['record']['seed'],
            source_arm=ref['record']['arm'],wire=info(wire),prefix_count=n,entry_hash=digest(state),domain=domain,
            previous=parent,choices=choices,baseline_id=candidate_id(baseline),
            keep_all_id=candidate_id(next(c for c in choices if not indexes(c))),
            status_only_id=candidate_id(next(c for c in choices if indexes(c)==status_indices)),
            expected_final_hash=end_hash,expected_status=end_status,expected_hp=end_hp,
            context=state['context'],entry_hp=state['player']['hp'],
            cards=[{k:c.get(k) for k in ('index','name','id','type','cost','upgraded')} for c in state['cards']]))
    assert len({r['seed'] for r in roots})==1
    return dict(manifest=v,sources=[info(source_path),info(certificate_path)],roots=roots,
        policy_sources=[info(ROOT/f) for f in ['rsi/opening_subset.py','rsi/continuation.py','rsi/teacher.py',
            'rsi/planner.py','rsi/ppo_actions.py','rsi/potions.py']],
        budgets=dict(wall_seconds=900,trial_seconds=120,replay_seconds=120,actions=300,workers=4),
        ranking='True clear, remaining HP, retained potion count; dead inventory has zero utility; tie fewer discards then lexical indices.',
        comparison='Full bank oracle vs frozen baseline, keep-all, status/curse-only; each fixes the first action only.',
        scope='One source seed, five correlated known roots; no model calls, synthetic game edits or default promotion.')


def trial(root,choice,v,deadline,tag='candidate'):
    ident=candidate_id(choice);trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),
        {**v,'scope':root.get('scope','E169_known_opening_counterfactual'),'root':root['case'],'opening':choice['action'],'tag':tag})
    started=time.monotonic();engine=None;state={};previous=root['previous'];program=FrozenProgram(previous);trans=[]
    r=dict(case=root['case']+'-'+ident+'-'+tag,root=root['case'],candidate_id=ident,tag=tag,
        discard_indices=indexes(choice),status='unstarted',steps=0,illegal_actions=0,restore_seconds=0.)
    def send(c):
        left=min(120-(time.monotonic()-started),deadline-time.monotonic())
        if left<=0:raise TimeoutError('Opening trial/global cap')
        engine.timeout=min(15,left);return engine.send(c)
    try:
        if time.monotonic()>=deadline:raise TimeoutError('Not started before global cap')
        r['status']='error';assert info(ROOT/root['wire']['path'])==root['wire']
        pairs=wire_pairs(ROOT/root['wire']['path']);engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs[:root['prefix_count']]):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch at command {i+1}')
        assert digest(state)==root['entry_hash'];r['restore_seconds']=time.monotonic()-started
        r['prefix_commands_verified']=root['prefix_count']
        for step in range(301):
            end=boundary(state)
            if end:r['status']=end;break
            if step==300:raise TimeoutError('Opening action cap')
            choices=legal_choices(state,{})
            if step==0:
                if digest(state)!=root['domain']['state_hash']:raise ValueError('Stale opening domain')
                chosen=next(c for c in choices if c['action']==choice['action'])
                meta=dict(selection_effect=root['domain']['effect'],route='forced_opening_counterfactual')
            else:chosen,meta=program.choose(state,choices,previous)
            if chosen['action'] not in [c['action'] for c in choices]:
                r['illegal_actions']+=1;raise ValueError('Illegal current choice')
            trace.write('decision',dict(before=digest(state),state=state,chosen=chosen,**meta))
            before=digest(state);program.remember(state,chosen);state=send(chosen['action']);previous=chosen;r['steps']+=1
            trans.append(dict(before=before,action=chosen['action'],after=digest(state)))
        r.update(hp=state['player']['hp'],potions=[p['id'] for p in state['player']['potions']],
            final_hash=digest(state),transition_hash=digest(trans),
            original_final_match=digest(state)==root['expected_final_hash'] if 'expected_final_hash' in root else None)
    except TimeoutError as exc:r.update(status='timeout',error=str(exc))
    except Exception as exc:r.update(status='error',error=f'{type(exc).__name__}: {exc}')
    finish(trace,r,engine,started);return r


def evaluate(v,path,output):
    p=checked(path,tracked=True);same_runtime(p,v)
    for s in p['sources']+p['policy_sources']:assert info(ROOT/s['path'])==s
    started=time.monotonic();deadline=started+900;directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    def run_item(item):
        root,choice,tag=item;r=trial(root,choice,v,deadline,tag)
        write(directory/(r['case']+'.json'),r);return r
    # Baselines first; every other candidate remains in the bank and is charged.
    ordered={r['case']:sorted(r['choices'],key=lambda c:(candidate_id(c)!=r['baseline_id'],len(indexes(c)),indexes(c))) for r in p['roots']}
    jobs=[(r,ordered[r['case']][i],'candidate') for i in range(32) for r in p['roots']]
    records=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(run_item,jobs):
            records.append(r)
            if len(records)%10==0:print(json.dumps(dict(completed=len(records),total=len(jobs))),flush=True)
    summaries=[];verification_jobs=[];choices=[]
    for root in p['roots']:
        rs=[r for r in records if r['root']==root['case']]
        good=[r for r in rs if r['status'] in ('clear','defeat') and not r.get('error')]
        base=next(r for r in rs if r['candidate_id']==root['baseline_id'])
        if len(good)!=len(rs):
            summaries.append(dict(case=root['case'],complete=False,candidates=len(rs),valid=len(good)));continue
        best=pick(rs);keep=next(r for r in rs if r['candidate_id']==root['keep_all_id'])
        simple=next(r for r in rs if r['candidate_id']==root['status_only_id'])
        compact=lambda r:{k:r[k] for k in ('candidate_id','discard_indices','status','hp','potions','steps')}
        summaries.append(dict(case=root['case'],complete=True,candidates=len(rs),valid=len(good),
            clears=sum(r['status']=='clear' for r in rs),baseline=compact(base),selected=compact(best),
            keep_all=compact(keep),status_only=compact(simple),improved=rank(best)>rank(base),
            lost_clear=base['status']=='clear' and best['status']!='clear',
            baseline_original_match=base['original_final_match'],
            charged_trial_seconds=sum(r['seconds'] for r in rs),restore_seconds=sum(r['restore_seconds'] for r in rs)))
        # Persist selection before verifying; no choice can change after seeing verification.
        choices.append(dict(root=root['case'],candidate_id=best['candidate_id']))
        verification_jobs.extend([(base,'baseline'),(best,'selected')])
    write(directory/'frozen-selections.json',choices)
    def verify(item):
        r,role=item;proof=replay(r,v,seconds=max(.001,min(120,deadline-time.monotonic())))
        return dict(root=r['root'],candidate_id=r['candidate_id'],role=role,record=proof,
            matches=proof['status']=='match' and proof.get('final_hash')==r.get('final_hash'))
    with ThreadPoolExecutor(max_workers=4) as pool:proofs=list(pool.map(verify,verification_jobs))
    execute_jobs=[(root,next(c for c in root['choices'] if candidate_id(c)==s['candidate_id']),'selected_execution')
        for s in choices for root in p['roots'] if root['case']==s['root']]
    with ThreadPoolExecutor(max_workers=4) as pool:executed=list(pool.map(run_item,execute_jobs))
    matches=[]
    for r in executed:
        source=next(x for x in records if x['root']==r['root'] and x['candidate_id']==r['candidate_id'])
        matches.append(dict(root=r['root'],matches=r.get('final_hash')==source.get('final_hash')
            and r.get('transition_hash')==source.get('transition_hash') and r['status']==source['status']))
    raw=audit([records,proofs,executed]);seconds=time.monotonic()-started
    integrity=(len(records)==160 and len(proofs)==10 and len(executed)==5
        and all(s['complete'] and s['baseline_original_match'] for s in summaries)
        and all(r['status'] in ('clear','defeat') and not r.get('error') and r['illegal_actions']==0 for r in records+executed)
        and all(r['matches'] for r in proofs+matches) and raw['pass'] and seconds<=900)
    return dict(manifest=v,plan=info(path),records=records,summaries=summaries,proofs=proofs,executed=executed,
        execution_matches=matches,raw_audit=raw,seconds=seconds,integrity_pass=integrity,
        local_headroom_gate=integrity and any(s['improved'] for s in summaries) and not any(s['lost_clear'] for s in summaries),
        default_promotion=False,model_api_calls=0,full_runs_evaluated=0,distinct_seeds=1)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['plan','evaluate']);ap.add_argument('--plan',type=Path)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E169'}
    value=plan(v) if a.mode=='plan' else evaluate(v,a.plan,a.output)
    write(a.output,value)
    if a.mode=='evaluate':print(json.dumps({k:value[k] for k in ('integrity_pass','local_headroom_gate','seconds','summaries')}))
