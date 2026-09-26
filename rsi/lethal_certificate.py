"""Nominate simple leader lethal, then certify by exact accepted-prefix execution.

A numeric preview alone never authorizes an action. Only the pinned CLI is supported.
"""
import hashlib
import time
import uuid
from .engine import ROOT, Headless
from .policy import combat_candidates
from .teacher import is_minion, terminal
from .trace import Trace, digest

SUPPORTED_CARDS={'CARD.STRIKE_IRONCLAD','CARD.STRIKE_SILENT'}


def nominate(state, choices):
    if state.get('decision')!='combat_play' or state.get('context',{}).get('room_type')!='Boss':return []
    enemies=state.get('enemies',[]);leaders=[e for e in enemies if not is_minion(e)]
    if len(leaders)!=1:return []
    leader=leaders[0]
    if leader.get('hp',0)<=0:return []
    hand={c['index']:c for c in state.get('hand',[])};result=[]
    for c in choices:
        a=c['action'];args=a.get('args',{})
        card=hand.get(args.get('card_index'),{})
        if a['action']!='play_card' or card.get('id') not in SUPPORTED_CARDS or not card.get('can_play'):continue
        if args.get('target_index')!=leader['index']:continue
        preview=next((p for p in card.get('damage_by_target',[]) if p['target_index']==leader['index']),{})
        damage=preview.get('damage')
        if isinstance(damage,(int,float)) and damage>=leader['hp']+leader.get('block',0):result.append(c)
    return result


def probe(state, choice, prefix, manifest, parent_run):
    """Separate offline branch. Failure/ambiguity yields no certificate, never a win."""
    uid=str(uuid.uuid4());trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,'scope':'offline_one_action_lethal_probe','parent_run':parent_run})
    out={'probe_id':uid,'entry_hash':digest(state),'action':choice['action'],'certified':False,'status':'error'}
    engine=None;started=time.monotonic()
    try:
        engine=Headless(trace.directory)
        branch={}
        if any(c.get('cmd') not in ('start_run','action') for c in prefix):raise ValueError('Noncanonical prefix command')
        for cmd in prefix:branch=engine.send(cmd)
        if digest(branch)!=digest(state):raise ValueError('Probe entry mismatch')
        out['entry_verified']=True
        trace.write('entry',{'state':branch,'state_hash':digest(branch)})
        legal=combat_candidates(branch)
        if choice not in legal:raise ValueError('Probe choice not fresh legal')
        trace.write('candidates',legal);trace.write('selected',choice)
        after=engine.send(choice['action'])
        trace.write('after',{'state':after,'state_hash':digest(after)})
        out.update(status=terminal(after) or 'not_terminal',after_hash=digest(after),final_hp=after.get('player',{}).get('hp'))
        out['certified']=out['status']=='boss_clear' and out['final_hp']>0
    except Exception as exc:
        out['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',out['error'])
    finally:
        if engine:engine.close()
    out['seconds']=round(time.monotonic()-started,4)
    out['wire_sha256']=hashlib.sha256((trace.directory/'wire.jsonl').read_bytes()).hexdigest() if engine else None
    trace.write('summary',out);out['trace_path']=str(trace.path.relative_to(ROOT));out['trace_sha256']=trace.close()
    return out


def certify(state, choices, prefix, manifest, parent_run):
    reports=[]
    # At most one branch per decision: failure abstains instead of expensive search.
    nominated=nominate(state,choices)
    if not nominated:return None,None,reports
    choice=nominated[0];proof=probe(state,choice,prefix,manifest,parent_run);reports.append(proof)
    return (choice,proof,reports) if proof['certified'] else (None,None,reports)
