#!/usr/bin/env python3
"""Frozen wire labels, all historical replays and one bounded opening continuation."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import finish
from rsi.campaign_teacher import Ownership
from rsi.checkpoints import wire_pairs,file_hash
from rsi.continuation import FrozenProgram
from rsi.engine import Headless
from rsi.ownership_audit import labels,campaign_request_failures
from rsi.run_env import legal_choices,replay
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime


def plan(v):
    sources=[]
    for path in (ROOT/'experiments/E160/evaluation-v1.json',ROOT/'artifacts/runs/e165-evaluation-v1.json'):
        for r in checked(path)['records']:
            wire=(ROOT/r['trace_path']).parent/'wire.jsonl'
            assert file_hash(wire)==r['wire.jsonl_sha256']
            sources.append(dict(experiment=path.parent.name,record=r,wire=info(wire),labels=labels(wire_pairs(wire))))
    return dict(manifest=v,sources=sources,engine_source=info(ROOT/'vendor/sts2-cli/src/Sts2Headless/RunSimulator.cs'),
        source_evidence='DetectDecisionPoint pending selects precede CombatManager guard; CardRewardState has gold_earned; generated selection has from_event. Frozen wire neighbor labels, not combat_active.',
        continuation_run='cd9a5cb9-82d9-430e-ba29-05debd6f7974',
        budgets=dict(wall_seconds=600,actions=300,trial_seconds=120),model_api_calls=0)


def diagnostic(source,v,deadline):
    pairs=wire_pairs(ROOT/source['wire']['path']);trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),
        {**v,'scope':'E167_known_prefix_diagnostic'})
    r=dict(case='E165-A5-opening',status='error',steps=0,illegal_actions=0,teacher_requests=0)
    started=time.monotonic();engine=None;owner=Ownership();program=FrozenProgram(None);state={};previous=None;trans=[]
    def send(c):
        left=min(deadline-time.monotonic(),120-(time.monotonic()-started))
        if left<=0:raise TimeoutError('E167 budget')
        engine.timeout=min(15,left);return engine.send(c)
    try:
        engine=Headless(trace.directory,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs):
            state=send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Prefix mismatch {i}')
            if state.get('decision'):owner.observe(state)
        assert len(pairs)==306 and owner.active
        r['prefix_commands_verified']=len(pairs);r['opening_hash']=digest(state)
        for step in range(301):
            active,clear=owner.observe(state)
            if not active:
                r['status']='clear' if clear else 'defeat';break
            if step==300:raise TimeoutError('E167 action cap')
            choices=legal_choices(state,{})
            chosen,meta=program.choose(state,choices,previous)
            if chosen['action'] not in [c['action'] for c in choices]:
                r['illegal_actions']+=1;raise ValueError('Illegal choice')
            trace.write('decision',dict(before=digest(state),state=state,chosen=chosen,owner='program_combat',**meta))
            before=digest(state);program.remember(state,chosen);state=send(chosen['action']);previous=chosen
            trans.append(dict(before=before,action=chosen['action'],after=digest(state)));r['steps']+=1
        r.update(hp=state['player']['hp'],final_hash=digest(state),transition_hash=digest(trans))
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started);return r


def evaluate(v,path):
    p=checked(path,tracked=True);same_runtime(p,v)
    assert info(ROOT/p['engine_source']['path'])==p['engine_source']
    started=time.monotonic();deadline=started+600;rows=[];proofs=[];original_requests=[]
    for source in p['sources']:
        assert info(ROOT/source['wire']['path'])==source['wire']
        pairs=wire_pairs(ROOT/source['wire']['path']);assert labels(pairs)==source['labels']
        expected={r['command_number']:r for r in source['labels']};owner=Ownership();clears=0
        for i,(_,s) in enumerate(pairs,1):
            if not s.get('decision'):continue
            active,clear=owner.observe(s);clears+=clear
            if i in expected:rows.append(dict(run=source['record']['run_id'],command=i,
                expected=expected[i]['expected_owner'],actual='battle' if active else 'campaign',clear=clear))
        # Existing clear count counts actual boundaries, independent of selection label.
        original=source['record']['completed_battles']
        assert clears==original, (source['record']['case'],clears,original)
        events=[json.loads(x) for x in (ROOT/source['record']['trace_path']).read_text().splitlines()]
        original_requests.extend(dict(run=source['record']['run_id'],**x) for x in campaign_request_failures(events,pairs))
        proofs.append(replay(source['record'],v,seconds=min(120,deadline-time.monotonic())))
        print(json.dumps(dict(replayed=source['record']['run_id'],status=proofs[-1]['status'])),flush=True)
    target=next(s for s in p['sources'] if s['record']['run_id']==p['continuation_run'])
    continuation=diagnostic(target,v,deadline)
    proof=replay(continuation,v,seconds=min(120,deadline-time.monotonic()));proofs.append(proof)
    bundles=audit([proofs,[continuation]])
    seconds=time.monotonic()-started
    passed=(all(r['expected']==r['actual'] and not r['clear'] for r in rows)
        and all(r['status']=='match' for r in proofs) and bundles['pass'] and seconds<=600
        and continuation['status'] in ('clear','defeat') and not continuation.get('error')
        and continuation['illegal_actions']==0 and continuation['teacher_requests']==0)
    return dict(manifest=v,plan=info(path),selection_labels=rows,original_misrouted_requests=original_requests,
        continuation=continuation,replays=proofs,raw_audit=bundles,seconds=seconds,compatibility_gate=passed,
        full_run_wins=0,scope='Known prefixes only; no battle selection quality improvement claimed',model_api_calls=0)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['plan','evaluate']);ap.add_argument('--plan',type=Path)
    ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E167'}
    result=plan(v) if a.mode=='plan' else evaluate(v,a.plan)
    write(a.output,result)
    if a.mode=='evaluate':print(json.dumps({k:result[k] for k in ('compatibility_gate','seconds','continuation','original_misrouted_requests')}))
