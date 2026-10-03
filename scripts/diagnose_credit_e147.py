#!/usr/bin/env python3
"""Read-only E146 raw-trace audit. No engine actions, gradients or new outcomes."""
import argparse
from bisect import bisect_right
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.battle_search import boundary
from rsi.checkpoints import file_hash,wire_pairs
from rsi.phase_rl import phase_encode,controller
from rsi.ppo import advantages
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.pilot_onpolicy_e146 import reward


def measure(rows):
    if not rows:return {'n':0}
    value=np.array([x['value'] for x in rows]);ret=np.array([x['reward'] for x in rows]);err=ret-value
    variance=float(ret.var());multi=[x for x in rows if x['choices']>1]
    out=dict(n=len(rows),trajectories=len({x['case'] for x in rows}),forced=sum(x['choices']==1 for x in rows),
        multi=len(multi),mean_value=float(value.mean()),mean_return=float(ret.mean()),mse=float((err**2).mean()),
        return_variance=variance,explained_variance=1-float(err.var())/variance if variance>1e-12 else None,
        r2_vs_return_mean=1-float((err**2).mean())/variance if variance>1e-12 else None,
        value_positive=int((value>0).sum()),value_below_minus_one=int((value< -1).sum()),
        multi_entropy_mean=float(np.mean([x['entropy'] for x in multi])) if multi else None,
        multi_top_probability_mean=float(np.mean([x['top_probability'] for x in multi])) if multi else None)
    if 'adv' in rows[0]:
        out.update(positive_adv=sum(x['adv']>1e-8 for x in rows),
            negative_adv=sum(x['adv']< -1e-8 for x in rows),
            negative_to_positive=sum(x['raw_adv']< -1e-8 and x['adv']>1e-8 for x in rows),
            multi_absolute_adv=sum(abs(x['adv']) for x in multi),
            forced_absolute_adv=sum(abs(x['adv']) for x in rows if x['choices']==1))
    return out


def name(choice):
    detail=choice.get('details') or {}
    return detail.get('title',detail.get('name',choice.get('name',choice['action']['action'])))


def snapshot(state):
    p=state.get('player') or {}
    return dict(phase=state['decision'],context=state.get('context'),hp=p.get('hp'),max_hp=p.get('max_hp'),
        block=p.get('block'),energy=state.get('energy'),round=state.get('round'),
        hand=[{k:c.get(k) for k in ('index','name','cost','stats','can_play')} for c in state.get('hand',[])],
        enemies=[{k:e.get(k) for k in ('index','name','hp','block','intents','powers')} for e in state.get('enemies',[])],
        potions=p.get('potions',[]))


def load(record,terminal_reward):
    path=ROOT/record['trace_path'];wire=path.with_name('wire.jsonl')
    if file_hash(path)!=record['trace_sha256'] or file_hash(wire)!=record['wire.jsonl_sha256']:
        raise ValueError('Changed raw evidence')
    pairs=wire_pairs(wire);events=[json.loads(x)['data'] for x in path.read_text().splitlines() if json.loads(x)['kind']=='decision']
    if len(events)!=record['steps'] or len(pairs)!=len(events)+1:raise ValueError('Noncontiguous recorded actions')
    rows=[];active=False;clears=0
    for i,event in enumerate(events):
        s=pairs[i][1];after=pairs[i+1][1]
        if digest(s)!=event['before'] or pairs[i+1][0]!=event['chosen']['action']:
            raise ValueError('Decision/wire alignment failed')
        if active:
            outcome=boundary(s)
            if outcome:active=False;clears+=int(outcome=='clear')
        if s['decision']=='combat_play':active=True
        probs=np.asarray(event['probabilities'],dtype=np.float64);n=len(event['candidates'])
        if len(probs)!=n or not np.isclose(probs.sum(),1.,atol=1e-6) or (probs<0).any():raise ValueError('Invalid probabilities')
        index=event['index'];action=event['chosen']['action']['action']
        if event['candidates'][index]['action']!=event['chosen']['action']:
            raise ValueError('Chosen probability does not match executed action')
        hp=(s.get('player') or {}).get('hp');next_hp=(after.get('player') or {}).get('hp')
        rows.append(dict(case=record['case'],i=i,phase=s['decision'],ascension=record['ascension'],
            status=record['status'],value=event['value'],reward=terminal_reward,choices=n,
            probability=float(probs[index]),top_probability=float(probs.max()),
            entropy=float(-(probs[probs>0]*np.log(probs[probs>0])).sum()/np.log(n)) if n>1 else 0.,
            action=action,selected_name=name(event['chosen']),clears=clears,
            six_already_clear=clears>=6,hp=hp,next_hp=next_hp,
            death_after=after.get('decision')=='game_over' and not after.get('victory'),
            alternatives=[name(c) for j,c in enumerate(event['candidates']) if j!=index]))
    return rows,events,pairs


def group(rows,key):
    return {str(k):measure([x for x in rows if x[key]==k]) for k in sorted({x[key] for x in rows})}


def divergence(a,b,cache):
    ra,ea,pa=cache[a['case']];rb,eb,pb=cache[b['case']]
    out=dict(initial_case=a['case'],candidate_case=b['case'],seed=a['seed'],ascension=a['ascension'],
        initial_status=a['status'],candidate_status=b['status'],
        initial_trace_sha256=a['trace_sha256'],candidate_trace_sha256=b['trace_sha256'])
    for i,(x,y) in enumerate(zip(ea,eb)):
        if x['before']!=y['before']:raise ValueError('Shared history diverged before changed action')
        if x['chosen']['action']!=y['chosen']['action']:
            out.update(first_difference=i,state_hash=x['before'],state=snapshot(pa[i][1]),
                initial_action=x['chosen']['action'],candidate_action=y['chosen']['action'],
                initial_name=name(x['chosen']),candidate_name=name(y['chosen']),
                initial_top_probability=max(x['probabilities']),candidate_top_probability=max(y['probabilities']),
                initial_action_probability_in_candidate=next(y['probabilities'][j] for j,c in enumerate(y['candidates']) if c['action']==x['chosen']['action']),
                candidate_action_probability_in_initial=next(x['probabilities'][j] for j,c in enumerate(x['candidates']) if c['action']==y['chosen']['action']))
            return out
    out['first_difference']=None
    return out


def main(output):
    if output.exists():raise ValueError('Preserve previous audit')
    started=time.monotonic();deadline=started+900;torch.set_num_threads(1)
    tpath=ROOT/'experiments/E146/training-v1.json';epath=ROOT/'experiments/E146/evaluation-v1.json'
    training=json.loads(tpath.read_text());evaluation=json.loads(epath.read_text())
    report=dict(manifest={**manifest(),'experiment':'E147','scope':'read_only_trace_diagnosis'},
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in (tpath,epath)},training=[],dev={},divergences=[],rescoring=[],
        new_game_actions=0,gradient_updates=0,notes=['All value errors describe realized paths, not counterfactual optimal values.',
        'DEV policies are greedy; training critic targets concern stochastic six-battle continuation.',
        'Initial BC critic was trained for a different horizon; not a six-battle calibrated baseline.'])
    aggregate=[];details=[];fatal=[];selected=[];initials=[]
    for learner in training['learners']:
        for update in learner['updates']:
            if time.monotonic()>deadline:raise TimeoutError('Audit budget')
            batch=[]
            for record in update['episodes']:
                rows,events,pairs=load(record,reward(record));batch+=rows
                details.append(dict(case=record['case'],seed=record['seed'],learner=learner['learner'],update=update['update'],
                    ascension=record['ascension'],status=record['status'],steps=record['steps'],
                    forced=sum(x['choices']==1 for x in rows),reward=reward(record),first_value=rows[0]['value'],
                    last_value=rows[-1]['value'],last_action=rows[-1]['action'],last_choices=rows[-1]['choices'],
                    trace_path=record['trace_path'],trace_sha256=record['trace_sha256']))
                for x in rows:
                    if x['death_after']:
                        fatal.append({**x,'learner':learner['learner'],'update':update['update'],
                            'state_hash':events[x['i']]['before'],'state':snapshot(pairs[x['i']][1]),'trace_path':record['trace_path']})
                if update['update']==1 and record['case'].endswith('-00'):
                    selected.append((record,events,pairs))
                initials.append(rows[0])
            raw=np.asarray([x['reward']-x['value'] for x in batch],dtype=np.float32)
            normalized=(raw-raw.mean())/(raw.std()+1e-8)
            for row,a,b in zip(batch,raw,normalized):row.update(raw_adv=float(a),adv=float(b))
            report['training'].append(dict(learner=learner['learner'],update=update['update'],all=measure(batch),
                by_phase=group(batch,'phase'),by_ascension=group(batch,'ascension'),
                first_states=measure([x for x in batch if x['i']==0]),
                six_already_clear=measure([x for x in batch if x['six_already_clear']])))
            aggregate+=batch
            print(json.dumps(dict(learner=learner['learner'],update=update['update'],decisions=len(batch))),flush=True)
    report['training_overall']=dict(all=measure(aggregate),by_phase=group(aggregate,'phase'),by_ascension=group(aggregate,'ascension'),
        six_already_clear=measure([x for x in aggregate if x['six_already_clear']]),
        six_pending_actions=dict(Counter(x['action'] for x in aggregate if x['six_already_clear'])),
        six_pending_hp_changed=sum(x['hp']!=x['next_hp'] for x in aggregate if x['six_already_clear']),
        trajectory_lengths={str(q):float(np.quantile([d['steps'] for d in details],q)) for q in (0,.25,.5,.75,.95,1.)},
        fatal_multi=sum(x['choices']>1 for x in fatal),fatal_forced=sum(x['choices']==1 for x in fatal),
        fatal_mean_value=float(np.mean([x['value'] for x in fatal])))
    report['episodes']=details;report['training_fatal']=fatal
    cache={}
    for record in evaluation['records']:
        rr=reward(record) if record['horizon']=='six' else -1. if record['status']=='defeat' else None
        if rr is None:raise ValueError('Unregistered act-clear reward')
        cache[record['case']]=load(record,rr)
    for actor in evaluation['checkpoints']:
        rows=[x for r in evaluation['records'] if r['actor']==actor and r['horizon']=='six' for x in cache[r['case']][0]]
        episodes=[r for r in evaluation['records'] if r['actor']==actor and r['horizon']=='act1']
        report['dev'][actor]=dict(six=measure(rows),by_phase=group(rows,'phase'),
            fatal=[dict(**cache[r['case']][0][-1],state=snapshot(cache[r['case']][2][-2][1]),trace_path=r['trace_path']) for r in episodes if r['status']=='defeat'],
            outcome=evaluation['by_horizon']['six'][actor],
            act1_boss_entries=[dict(case=r['case'],entry=e) for r in episodes for e in r['entries'] if e['room_type']=='Boss'])
    for actor in ('1901','1902'):
        for b in [r for r in evaluation['records'] if r['actor']==actor and r['horizon']=='six']:
            a=next(r for r in evaluation['records'] if r['actor']=='initial' and r['horizon']=='six' and r['seed']==b['seed'])
            d=divergence(a,b,cache);d['actor']=actor
            d['paired']='gain' if b['status']=='curriculum_clear' and a['status']!='curriculum_clear' else 'regression' if a['status']=='curriculum_clear' and b['status']!='curriculum_clear' else 'tie'
            report['divergences'].append(d)
    models={k:load_phase(cp) for k,cp in evaluation['checkpoints'].items()}
    for record,events,pairs in selected:
        previous=None;rows=[]
        for event,(_,state) in zip(events,pairs):
            if time.monotonic()>deadline:raise TimeoutError('Audit re-scoring budget')
            predictions={name:controller(model)(state,event['candidates'],previous)[1] for name,model in models.items()}
            base=np.asarray(predictions['initial']['probabilities'],dtype=np.float64)
            for actor in ('1901','1902'):
                p=np.asarray(predictions[actor]['probabilities'],dtype=np.float64);valid=base>0
                rows.append(dict(actor=actor,phase=state['decision'],argmax_changed=int(np.argmax(base))!=int(np.argmax(p)),
                    old_to_new_kl=float((base[valid]*(np.log(base[valid])-np.log(p[valid].clip(1e-30)))).sum()),
                    selected_probability_before=float(base[event['index']]),selected_probability_after=float(p[event['index']]),
                    before_value=predictions['initial']['value'],after_value=predictions[actor]['value']))
            previous=event['chosen']
        report['rescoring'].append(dict(case=record['case'],source_trace_sha256=record['trace_sha256'],rows=rows))
    report['raw_audit']=audit([training,evaluation])
    checkpoints={}
    def visit(x):
        if isinstance(x,dict):
            if 'path' in x and 'sha256' in x and str(x['path']).endswith('.pt'):checkpoints[x['path']]=x['sha256']
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    visit([training,evaluation]);report['checkpoint_audit']={p:file_hash(ROOT/p)==h for p,h in checkpoints.items()}
    report['seconds']=time.monotonic()-started
    report['execution_pass']=report['raw_audit']['pass'] and all(report['checkpoint_audit'].values()) and len(details)==1152 and len(cache)==180 and len(aggregate)==103127
    write(output,report);print(json.dumps({k:report[k] for k in ('training_overall','seconds','execution_pass')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();main(args.output)
