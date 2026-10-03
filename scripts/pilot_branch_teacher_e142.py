#!/usr/bin/env python3
"""Training-only exact-engine branch teacher; no searched path is a full-run win."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.checkpoints import file_hash,wire_pairs
from rsi.trace import digest
from rsi.ppo import padded
from rsi.phase_rl import phase_encode
from rsi.ppo_actions import ACTION_SPACE,complete_choices,complete_baseline
from rsi.ppo_env import episode
from rsi.battle_search import compact
from scripts.evaluate_battle_search_e120 import manifest,write,audit
from scripts.pilot_fullpolicy_e140 import load_phase,require_train


def rank(r):
    if r['status'] not in ('clear','defeat'):raise ValueError('No rank for censored path')
    return (int(r['status']=='clear'),r['hp'] if r['status']=='clear' else 0)


def meaningful(candidate,control):
    return candidate['status']=='clear' and (control['status']=='defeat' or candidate['hp']>=control['hp']+5)


def alternatives(state,previous,model,index):
    choices=complete_choices(state);encoded=phase_encode(state,choices,previous,max_actions=4096)
    with torch.inference_mode():d,_=model(*padded([encoded]));greedy=int(d.probs[0].argmax())
    planner=complete_baseline(state,choices,previous)
    mandatory=[greedy,next(i for i,c in enumerate(choices) if c['action']==planner['action'])]
    mandatory += [i for i,c in enumerate(choices) if c['action']['action']=='end_turn']
    selected=list(dict.fromkeys(mandatory));rng=np.random.default_rng(142000+index)
    remaining=[i for i in range(len(choices)) if i not in selected]
    selected += list(map(int,rng.permutation(remaining)[:8-len(selected)]))
    return [choices[i] for i in selected],greedy,choices


def branch_policy(model,first,seed):
    rng=np.random.default_rng(seed)
    def policy(state,choices,previous,plan):
        with torch.inference_mode():
            d,v=model(*padded([phase_encode(state,choices,previous,max_actions=4096)]))
            p=d.probs[0].numpy().astype(np.float64);p/=p.sum()
        if not plan:index=next(i for i,c in enumerate(choices) if c['action']==first['action'])
        else:index=int(p.argmax()) if seed is None else int(rng.choice(len(p),p=p))
        return choices[index],dict(index=index,probabilities=p.tolist(),value=float(v[0]),forced_root=not plan,
                                   sampling='greedy' if seed is None else 'stochastic',policy_seed=seed)
    return policy


def roots():
    path=ROOT/'experiments/E139/bank-v1.json';bank=json.loads(path.read_text());out=[];sources=[]
    for r in bank['records']:
        if r['split']!='train' or r['index'] not in (0,1):continue
        require_train(r);sources.append(r)
        wire=(ROOT/r['trace_path']).with_name('wire.jsonl');pairs=wire_pairs(wire);e=r['entries'][-1]
        prefix=[c for c,_ in pairs[:e['command_count']]];state=pairs[e['command_count']-1][1]
        if digest(state)!=e['entry_hash']:raise ValueError('Changed fixed root')
        out.append((dict(case=r['case']+'-b'+str(e['ordinal']),prefix=prefix,prefix_hash=digest(prefix),entry_hash=e['entry_hash'],
            previous=e['previous'],character=r['character'],ascension=r['ascension'],act=e['act'],room_type=e['room_type'],
            source_case=r['case']),state))
    if len(out)!=30:raise ValueError('Changed source cohort')
    proof=audit(sources)
    if not proof['pass']:raise ValueError('Source evidence changed')
    return out,dict(sha256=file_hash(path),audit=proof)


def main(output):
    if output.exists():raise ValueError('Keep previous evidence')
    torch.set_num_threads(1);started=time.monotonic();deadline=started+900
    v={**manifest(),'experiment':'E142','ppo_action_space':ACTION_SPACE,'torch':str(torch.__version__),'encoder':'e140-phase-context-v1'}
    adapter=json.loads((ROOT/'experiments/E141/observations-v1.json').read_text())
    if not adapter['passed'] or adapter['manifest']['headless_assembly_sha256']!=v['headless_assembly_sha256']:
        raise ValueError('Observer adapter proof missing')
    cp=json.loads((ROOT/'experiments/E140/training-v2.json').read_text())['learners'][1]['bc']
    model=load_phase(cp);fixtures,source=roots();directory=output.with_suffix('');directory.mkdir(exist_ok=False,parents=True)
    def run(item):
        index,(f,state)=item;row=dict(case=f['case'],character=f['character'],ascension=f['ascension'],act=f['act'],room_type=f['room_type'],status='error',branches=[])
        def battle(label,**kw):
            return episode(f,v,label,encoder=phase_encode,seconds=min(30,max(.001,deadline-time.monotonic())),**kw)[0]
        control=battle('control',model=model);row['control']=compact(control)
        if control['status'] not in ('clear','defeat'):
            row['error']='Incomplete control';write(directory/(f['case']+'.json'),row);return row
        alts,greedy,choices=alternatives(state,f['previous'],model,index)
        row.update(legal_count=len(choices),selected_actions=[a['action'] for a in alts],greedy_action=choices[greedy]['action'])
        best=control;best_label='control'
        for j,first in enumerate(alts):
            for mode in ('greedy','stochastic'):
                seed=None if mode=='greedy' else 14200000+index*100+j
                label=f'branch{j}:{mode}'
                r=battle(label,policy=branch_policy(model,first,seed))
                row['branches'].append(dict(first_action=first['action'],continuation=mode,**compact(r)))
                if r['status'] in ('clear','defeat') and rank(r)>rank(best):best=r;best_label=label
        row['complete']=all(r['status'] in ('clear','defeat') for r in row['branches'])
        row['selected']=compact(best);row['selected_label']=best_label
        row['meaningful_gain']=meaningful(best,control)
        row['first_action_changed']=bool(best['plan'] and best['plan'][0]['action']!=row['greedy_action'])
        row['greedy_only_gain']=any(r['continuation']=='greedy' and r['status'] in ('clear','defeat') and meaningful(r,control) for r in row['branches'])
        row['potion_delta']=len(best.get('potions',[]))-len(control.get('potions',[]))
        if row['meaningful_gain']:
            replay=battle('selected:independent-replay',expected=best['plan']);row['verification']=compact(replay)
            row['verified']=replay['status']==best['status'] and replay['plan']==best['plan'] and replay.get('final_hash')==best['final_hash']
        else:row['verified']=True
        row['status']='complete' if row['complete'] and row['verified'] else 'invalid'
        write(directory/(f['case']+'.json'),row)
        print(json.dumps({k:row[k] for k in ('case','status','meaningful_gain','greedy_only_gain','selected_label')}|{'control':control['status'],'best':best['status']}),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(run,enumerate(fixtures)))
    complete=all(r['status']=='complete' for r in records)
    report=dict(manifest=v,source=source,checkpoint=cp,adapter_proof_sha256=file_hash(ROOT/'experiments/E141/observations-v1.json'),records=records,
                seconds=time.monotonic()-started,full_run_victories=0,scope='training-only branch search')
    report['summary']=dict(roots=30,complete=complete,meaningful_gains=sum(r.get('meaningful_gain',False) for r in records),
        greedy_only_gains=sum(r.get('greedy_only_gain',False) for r in records),
        control_clears=sum(r.get('control',{}).get('status')=='clear' for r in records),
        selected_clears=sum(r.get('selected',{}).get('status')=='clear' for r in records),
        changed_first_action_gains=sum(r.get('meaningful_gain',False) and r.get('first_action_changed',False) for r in records),
        trajectories=sum(1+len(r['branches'])+int('verification' in r) for r in records),
        branch_statuses=dict(Counter(p['status'] for r in records for p in r['branches'])))
    report['audit']=audit(report)
    report['teacher_gate']=complete and report['summary']['meaningful_gains']>=6 and report['audit']['pass']
    write(output,report);print(json.dumps({k:report[k] for k in ('summary','teacher_gate','seconds','audit')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
