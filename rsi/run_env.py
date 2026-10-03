"""Full natural runs, all legal decision phases, one private engine per attempt."""
from collections import Counter
import time
import uuid

import numpy as np
import torch

from .battle_search import boundary, finish, macro_choice
from .checkpoints import file_hash, wire_pairs
from .engine import ROOT, Headless
from .full import macro_candidates
from .ppo import encode, padded
from .ppo_actions import ACTION_LIMIT, complete_choices, complete_baseline
from .resources import require_resource_interface
from .trace import Trace, digest


def run_outcome(state):
    if state.get('decision') == 'game_over':
        return 'victory' if state.get('victory') else 'defeat'
    return None


def act_transition(state, target, boss_seen):
    """Research boundary: a real, living next-act map after encountering the boss."""
    if target is None or run_outcome(state) is not None:
        return False
    context = state.get('context') or {}
    act = context.get('act', 0)
    if act <= target:
        return False
    if (act != target + 1 or not boss_seen or state.get('decision') != 'map_select'
            or context.get('room_type') != 'Map' or state.get('player', {}).get('hp', 0) <= 0):
        raise ValueError('Unexpected act boundary; refusing to continue past the configured target')
    return True


def battle_transition(state, target, clears):
    """Stop only on a living map after all rewards for the target battle."""
    if target is None or clears < target or run_outcome(state) is not None:
        return False
    if clears != target or state.get('decision') == 'combat_play':
        raise ValueError('Unexpected battle boundary; refusing to start another battle')
    if state.get('decision') != 'map_select':
        return False
    if state.get('player', {}).get('hp', 0) <= 0:
        raise ValueError('Curriculum map is not alive')
    return True


def legal_choices(state, history):
    if state.get('decision') in ('combat_play', 'card_select'):
        return complete_choices(state)
    return macro_candidates(state, history, resource_decisions=True)


def run(config, manifest, model=None, controller=None, seconds=180, actions=2400, macro_controller=None,
        stop_after_act=None, stop_after_battles=None):
    if stop_after_act not in (None, 1, 2):
        raise ValueError('Research act boundary must be 1, 2 or None for a full run')
    if stop_after_battles is not None and (type(stop_after_battles) is not int or stop_after_battles < 1 or stop_after_act is not None):
        raise ValueError('Research battle boundary must be a positive integer, exclusive of act boundary')
    trace = Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()), {**manifest,'scope':manifest.get('experiment','E139')+'_run','config':config,
                  'stop_after_act':stop_after_act,'stop_after_battles':stop_after_battles})
    start=time.monotonic();deadline=start+seconds
    r={**config,'status':'error','steps':0,'entries':[],'scenes':Counter(),'phase_seconds':Counter(),
       'action_counts':Counter(),'cards_seen':set(),'relics_seen':set(),'acts_seen':set(),'max_floor':0,
       'illegal_actions':0,'network_calls':0,'planner_calls':0,'transitions':[],
       'stop_after_act':stop_after_act,'target_boss_seen':False,
       'stop_after_battles':stop_after_battles,'completed_battles':0}
    state={};previous=None;history={};active=False;engine=None;last=None;unchanged=0
    def send(command):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Full-run time cap')
        engine.timeout=min(15,remaining)
        clock=time.monotonic();s=engine.send(command);r['phase_seconds']['engine_send']+=time.monotonic()-clock
        return s
    try:
        clock=time.monotonic();engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        r['phase_seconds']['engine_start']=time.monotonic()-clock
        state=send(dict(cmd='start_run',**{k:config[k] for k in ('seed','character','ascension')}))
        require_resource_interface(state)
        for step in range(actions+1):
            context=state.get('context') or {};p=state.get('player') or {}
            r['max_floor']=max(r['max_floor'],state.get('floor') or context.get('floor') or 0)
            if context.get('act'):r['acts_seen'].add(context['act'])
            r['cards_seen'].update(c.get('id',c.get('name')) for c in p.get('deck',[]))
            r['relics_seen'].update(c.get('id',c.get('name')) for c in p.get('relics',[]))
            terminal=run_outcome(state)
            if terminal:r['status']=terminal;break
            if active:
                outcome=boundary(state)
                if outcome:
                    active=False
                    r['completed_battles']+=int(outcome=='clear')
            if act_transition(state,stop_after_act,r['target_boss_seen']):
                r['status']='act_clear';break
            if battle_transition(state,stop_after_battles,r['completed_battles']):
                r['status']='curriculum_clear';break
            if step==actions:r['status']='action_cap';break
            before=digest(state);unchanged=unchanged+1 if last==before else 0;last=before
            if unchanged>=5:raise ValueError('Six repeated states; no progress')
            d=state['decision']
            if d=='combat_play' and context.get('room_type')=='Boss' and context.get('act')==stop_after_act:
                r['target_boss_seen']=True
            if d=='combat_play' and not active:
                active=True
                r['entries'].append(dict(ordinal=len(r['entries'])+1,command_count=step+1,
                    entry_hash=before,previous=previous,act=context.get('act'),floor=context.get('floor'),
                    room_type=context.get('room_type'),enemies=[e['name'] for e in state['enemies']],
                    hp=p.get('hp'),max_hp=p.get('max_hp'),deck_hash=digest(p.get('deck')),
                    deck_size=p.get('deck_size'),potions=len(p.get('potions',[]))))
            clock=time.monotonic();choices=legal_choices(state,history)
            r['phase_seconds']['choices']+=time.monotonic()-clock
            payload=dict(before=before,candidates=choices)
            neural=config['arm']=='neural_all' or (config['arm']=='neural_combat' and active)
            if controller is not None:
                clock=time.monotonic()
                selected,extra=controller(state,choices,previous);payload.update(extra)
                r['phase_seconds']['controller_including_encode']+=time.monotonic()-clock
                r['network_calls']+=1
            elif neural:
                clock=time.monotonic();encoded=encode(state,choices,previous,max_actions=ACTION_LIMIT)
                r['phase_seconds']['encode']+=time.monotonic()-clock
                clock=time.monotonic()
                with torch.inference_mode():
                    dist,v=model(*padded([encoded]));probs=dist.probs[0].numpy()
                    index=int(np.argmax(probs));selected=choices[index]
                r['phase_seconds']['network']+=time.monotonic()-clock
                payload.update(index=index,probabilities=probs.tolist(),value=float(v[0]),old_logprob=float(dist.logits[0,index]))
                r['network_calls']+=1
            else:
                clock=time.monotonic()
                selected=complete_baseline(state,choices,previous) if active or d=='card_select' else (macro_controller or macro_choice)(state)
                r['phase_seconds']['planner']+=time.monotonic()-clock;r['planner_calls']+=1
            matches=[i for i,c in enumerate(choices) if c['action']==selected['action']]
            if not matches:r['illegal_actions']+=1;raise ValueError('Choice outside legal menu')
            payload.update(chosen=selected,index=matches[0]);trace.write('decision',payload)
            if d=='map_select':history['removed_here']=False
            if selected['action']['action']=='remove_card':history['removed_here']=True
            r['scenes'][d]+=1;r['action_counts'][selected['action']['action']]+=1
            state=send(selected['action']);r['steps']+=1
            r['transitions'].append(dict(before=before,action=selected['action'],after=digest(state)))
            previous=selected
    except TimeoutError as exc:r.update(status='timeout',error=str(exc))
    except Exception as exc:r.update(status='error',error=f'{type(exc).__name__}: {exc}')
    r.update(final_hash=digest(state),transition_hash=digest(r.pop('transitions')),
             final_context=state.get('context'),final_hp=state.get('player',{}).get('hp'),
             final_max_hp=state.get('player',{}).get('max_hp'))
    for k in ('cards_seen','relics_seen','acts_seen'):r[k]=sorted(r[k])
    finish(trace,r,engine,start)
    return r


def replay(record, manifest, seconds=180):
    source=ROOT/record['trace_path'];wire=source.with_name('wire.jsonl')
    if file_hash(source)!=record['trace_sha256'] or file_hash(wire)!=record['wire.jsonl_sha256']:
        raise ValueError('Changed full-run reference')
    pairs=wire_pairs(wire)
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'E139_independent_replay','case':record['case']})
    start=time.monotonic();engine=None;r=dict(case=record['case'],status='error',steps=0)
    boss_seen=False;target=record.get('stop_after_act')
    battle_target=record.get('stop_after_battles');active=False;clears=0
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(command,expected) in enumerate(pairs):
            remaining=seconds-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError('Full replay cap')
            engine.timeout=min(15,remaining);state=engine.send(command)
            if digest(state)!=digest(expected):raise ValueError(f'Full replay diverged at command {i}')
            c=state.get('context') or {}
            if state.get('decision')=='combat_play' and c.get('room_type')=='Boss' and c.get('act')==target:
                boss_seen=True
            if battle_target is not None:
                if active:
                    outcome=boundary(state)
                    if outcome:
                        active=False;clears+=int(outcome=='clear')
                if state.get('decision')=='combat_play':active=True
                if battle_transition(state,battle_target,clears) and i!=len(pairs)-1:
                    raise ValueError('Replay continued past curriculum boundary')
            r['steps']+=1
        terminal=run_outcome(state)
        if act_transition(state,target,boss_seen):terminal='act_clear'
        if battle_transition(state,battle_target,clears):terminal='curriculum_clear'
        if record['status']=='curriculum_clear' and terminal!='curriculum_clear':raise ValueError('Curriculum replay lacks true boundary')
        if record['status']=='act_clear' and terminal!='act_clear':raise ValueError('Act-clear replay lacks true boundary')
        r.update(status='match',outcome=terminal,final_hash=digest(state))
    except Exception as exc:r.update(error=f'{type(exc).__name__}: {exc}')
    finish(trace,r,engine,start)
    return r
