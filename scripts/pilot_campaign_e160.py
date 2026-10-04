#!/usr/bin/env python3
"""Four paired natural runs; treatment choices are committed online by this Astra task."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.campaign_teacher import episode,TeacherBudget,validate
from rsi.checkpoints import file_hash,wire_pairs
from rsi.run_env import replay
from rsi.trace import digest
from rsi.ownership_audit import campaign_request_failures
from scripts.pilot_root_teacher_e149 import checked,info,version,same_runtime
from scripts.evaluate_battle_search_e120 import write,audit


def plan(v):
    return dict(manifest=v,cases=[dict(case=f'A{a}-{i:03}',seed=f'e160_campaign_Ironclad_A{a}_{i:03}',
        character='Ironclad',ascension=a) for a in (0,5) for i in range(2)],
        arms=['program_campaign','astra_campaign'],
        budgets=dict(actions=2400,run_compute=120,request_seconds=600,packets_per_run=90,
                     packets_global=200,wall=5400,cpu=1200,workers=8),
        controller_sources=[info(p) for p in sorted((ROOT/'rsi').glob('*.py'))],
        initial_engine_certificate=info(ROOT/'experiments/E158/validation-v1.json'),
        tactical='FrozenProgram: legacy triggers/retaliation, early permitted potions; no Astra combat action',
        macro='program: existing cautious macro; treatment: fresh Astra choices plus explicit reservations',
        response_protocol='fresh case/run/seq/state hash; one legal choice; committed before action',
        gate='8terminals+8replays+trace/teacher/ownership/budget; >=2/4positive progress pairs, positive pooled progress, no negative mean by difficulty and no lost baseline victory; exploratory only',
        progress='lexicographic (victory, completed acts, cleared fights); components always reported',
        final_acceptance_seeds_unused=True,known_unsupported=['Trial #294','Crystal Sphere #64'])


def teacher_audit(records):
    failures=[];decisions=0;responses=0
    for r in records:
        events=[json.loads(s) for s in (ROOT/r['trace_path']).read_text().splitlines()]
        pairs=wire_pairs((ROOT/r['trace_path']).parent/'wire.jsonl')
        failures.extend([r['case'],'independent battle request',f]
                        for f in campaign_request_failures(events,pairs))
        requests={e['data']['seq']:e['data'] for e in events if e['kind']=='campaign_request'}
        for event in events:
            if event['kind']=='decision':
                d=event['data'];decisions+=1
                if d['owner']=='astra_campaign' and d['combat_active']:failures.append([r['case'],'combat takeover'])
                if d['chosen']['action'] not in [x['action'] for x in d['candidates']]:failures.append([r['case'],'illegal choice'])
            elif event['kind']=='campaign_response':
                d=event['data'];responses+=1;request=requests[d['seq']]
                raw=subprocess.check_output(['git','show',d['commit']+':'+d['path']],cwd=ROOT)
                packet=json.loads(raw);chosen=validate(packet,request)
                if digest(packet)!=d['packet_hash'] or digest(request)!=d['request_hash'] or chosen['action']!=d['choice']:
                    failures.append([r['case'],'changed packet'])
        if len(requests)!=r['expert_packets']:failures.append([r['case'],'request count'])
    return dict(passed=not failures,failures=failures,decisions=decisions,responses=responses)


def summarize(records):
    pairs=[]
    for case in dict.fromkeys(r['case'] for r in records):
        arms={r['arm']:r for r in records if r['case']==case};b=arms['program_campaign'];t=arms['astra_campaign']
        progress=lambda x:(int(x['status']=='victory'),x['completed_acts'],x['completed_battles'])
        delta=1 if progress(t)>progress(b) else -1 if progress(t)<progress(b) else 0
        pairs.append(dict(case=case,ascension=b['ascension'],baseline=progress(b),treatment=progress(t),sign=delta,
            lost_victory=b['status']=='victory' and t['status']!='victory'))
    by_asc={str(a):sum(p['sign'] for p in pairs if p['ascension']==a)/2 for a in (0,5)}
    return dict(pairs=pairs,positive_pairs=sum(p['sign']>0 for p in pairs),mean_progress_sign=sum(p['sign'] for p in pairs)/4,
        by_ascension=by_asc,progress_gate=sum(p['sign']>0 for p in pairs)>=2 and sum(p['sign'] for p in pairs)>0 and
            all(x>=0 for x in by_asc.values()) and not any(p['lost_victory'] for p in pairs),
        arms={arm:dict(victories=sum(r['status']=='victory' for r in records if r['arm']==arm),
            act2=sum(r['completed_acts']>=1 for r in records if r['arm']==arm),
            act3=sum(r['completed_acts']>=2 for r in records if r['arm']==arm),
            completed_battles=[r['completed_battles'] for r in records if r['arm']==arm])
            for arm in ('program_campaign','astra_campaign')})


def evaluate(v,plan_path,output):
    p=checked(plan_path,tracked=True);same_runtime(p,v)
    for source in p['controller_sources']:
        if info(ROOT/source['path'])!=source:raise ValueError('Frozen controller source changed')
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    pending=ROOT/'artifacts/runs/e160-pending'
    if pending.exists() and list(pending.glob('*.json')):raise ValueError('Pending previous run; do not overwrite')
    start=time.monotonic();deadline=start+p['budgets']['wall'];budget=TeacherBudget(p['budgets']['packets_global'])
    configs=[{**c,'arm':a} for c in p['cases'] for a in p['arms']]
    def one(config):
        r=episode(config,v,budget,pending,deadline)
        # Baseline outcomes stay out of the shared console until all expert decisions end.
        write(directory/(config['case']+'-'+config['arm']+'.json'),r)
        if config['arm']=='astra_campaign':print(json.dumps(dict(finished=config['case'],status=r['status'],error=r.get('error'))),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(one,configs))
    # No new expert decision after this point; contemporary baseline results may now be inspected.
    for r in records:
        if r['status'] in ('victory','defeat') and time.monotonic()<deadline:
            budget.check_cpu();r['verification']=replay(r,v,seconds=min(120,deadline-time.monotonic()))
    proof=audit(records);teachers=teacher_audit(records);seconds=time.monotonic()-start;used=budget.cpu()-budget.cpu_start
    complete=all(r['status'] in ('victory','defeat') and r.get('verification',{}).get('status')=='match' for r in records)
    summary=summarize(records) if complete else dict(progress_gate=False,incomplete=True)
    integrity=complete and proof['pass'] and teachers['passed']
    costs=dict(expert_packets=sum(r['expert_packets'] for r in records),
        input_chars=sum(r['expert_input_chars'] for r in records),output_chars=sum(r['expert_output_chars'] for r in records),
        wait_seconds=sum(r['expert_wait_seconds'] for r in records),tokens=None,usd=None)
    budget_pass=seconds<=5400 and used<=1200 and costs['expert_packets']<=200 and all(r['compute_seconds']<=120 for r in records)
    return dict(manifest=v,plan=info(plan_path),records=records,summary=summary,raw_audit=proof,teacher_audit=teachers,
        seconds=seconds,cpu_seconds=used,costs=costs,integrity=integrity,budget_pass=budget_pass,
        continuation_gate=integrity and budget_pass and summary['progress_gate'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('plan','evaluate'));p.add_argument('--plan',type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('Never overwrite an attempt')
    v={**version(),'experiment':'E160'}
    result=plan(v) if a.mode=='plan' else evaluate(v,a.plan,a.output)
    write(a.output,result)
    print(json.dumps({k:result[k] for k in ('summary','seconds','costs','integrity','continuation_gate') if k in result}),flush=True)
