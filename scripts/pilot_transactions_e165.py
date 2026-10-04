#!/usr/bin/env python3
"""Two fresh hybrid runs, independent expert budgets, blinded paired controls."""
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
from rsi.macro_transaction import automatic
from rsi.run_env import replay
from rsi.subset_action import validate_fresh
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime


def plan(v):
    return dict(manifest=v,cases=[dict(case=f'A{a}-000',seed=f'e165_hybrid_Ironclad_A{a}_000',character='Ironclad',ascension=a) for a in (0,5)],
        arms=['program_campaign','astra_campaign'],budgets=dict(packets_per_run=120,actions=2400,compute=120,reply=600,wall=3600,cpu=1200,workers=4),
        controller_sources=[info(p) for p in sorted((ROOT/'rsi').glob('*.py'))],
        baseline='E160 cautious campaign + FrozenProgram',treatment='Fresh Astra macro transactions + E161 subsets + E162 acquire/reserve; SAME FrozenProgram combat',
        final_acceptance_seeds_unused=True,gate='4 genuine terminals+4 exact replays+all integrity/budgets; >=1 positive progress pair and no negative pair; no default promotion')


def teacher_audit(records):
    failures=[];total=0;avoided=0;by_owner={};transactions=0
    for r in records:
        events=[json.loads(l) for l in (ROOT/r['trace_path']).read_text().splitlines()];requests={}
        for e in events:
            d=e['data']
            if e['kind']=='campaign_request':requests[d['seq']]=d
            if e['kind']=='campaign_response':
                raw=subprocess.check_output(['git','show',d['commit']+':'+d['path']],cwd=ROOT)
                packet=json.loads(raw);req=requests[d['seq']]
                chosen=validate(packet,req)
                if digest(packet)!=d['packet_hash'] or digest(req)!=d['request_hash'] or chosen['action']!=d['choice']:
                    failures.append([r['case'],'teacher binding'])
                total+=1
            if e['kind']!='decision':continue
            if d.get('selection_contract'):validate_fresh(d['state'],d['chosen'])
            elif d['chosen']['action'] not in [c['action'] for c in d['candidates']]:failures.append([r['case'],'illegal'])
            owner=d['owner'];by_owner[owner]=by_owner.get(owner,0)+1
            if owner.startswith(('astra','campaign_')) and d['combat_active']:failures.append([r['case'],'combat takeover'])
            if owner=='campaign_mechanical' and automatic(d['state'],d['candidates'])!=d['chosen']:
                failures.append([r['case'],'mechanical rule'])
            if owner=='campaign_transaction':
                transactions+=1
                if not d.get('transaction_binding'):failures.append([r['case'],'unbound transaction'])
            nontrivial=(d.get('selection_contract',{}).get('legal_subsets',0)>1 or len(d['candidates'])>1)
            if owner in ('campaign_transaction','campaign_mechanical') and nontrivial:avoided+=1
        if len(requests)!=r['expert_packets']:failures.append([r['case'],'packet count'])
    return dict(passed=not failures,failures=failures,expert_packets=total,owners=by_owner,
        avoided_nontrivial_requests=avoided,one_action_protocol_equivalent=total+avoided,
        note='Equivalent requests are same-trajectory accounting, not a randomized protocol comparison',transaction_actions=transactions)


def evaluate(v,plan_path,output):
    p=checked(plan_path,tracked=True);same_runtime(p,v)
    for s in p['controller_sources']:
        if info(ROOT/s['path'])!=s:raise ValueError('Controller changed')
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    pending=ROOT/'artifacts/runs/e165-pending'
    if pending.exists() and list(pending.glob('*.json')):raise ValueError('Outstanding request')
    start=time.monotonic();cpu_start=TeacherBudget.cpu();deadline=start+3600
    configs=[dict(**c,arm=arm,macro_transactions=arm=='astra_campaign',acquire_reservation=arm=='astra_campaign',
        factored_campaign_selection=arm=='astra_campaign',packet_limit=120) for c in p['cases'] for arm in p['arms']]
    def one(c):
        budget=TeacherBudget(120)
        r=episode(c,v,budget,pending,deadline)
        write(directory/(c['case']+'-'+c['arm']+'.json'),r)
        if c['arm']=='astra_campaign':print(json.dumps(dict(finished=c['case'],status=r['status'],error=r.get('error'))),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(one,configs))
    for r in records:
        r['verification']=replay(r,v,seconds=120)
    pairs=[]
    for case in p['cases']:
        by={r['arm']:r for r in records if r['case']==case['case']};b=by['program_campaign'];t=by['astra_campaign']
        progress=lambda r:(int(r['status']=='victory'),r['completed_acts'],r['completed_battles'])
        pairs.append(dict(case=case['case'],baseline=progress(b),treatment=progress(t),sign=(progress(t)>progress(b))-(progress(t)<progress(b))))
    teachers=teacher_audit(records);proof=audit(records);seconds=time.monotonic()-start;cpu=TeacherBudget.cpu()-cpu_start
    complete=all(r['status'] in ('victory','defeat') and r['verification']['status']=='match' for r in records)
    budget_pass=seconds<=3600 and cpu<=1200 and all(r['expert_packets']<=120 and r['compute_seconds']<=120 for r in records)
    result=dict(manifest=v,plan=info(plan_path),records=records,pairs=pairs,teacher_audit=teachers,raw_audit=proof,
        complete=complete,budget_pass=budget_pass,seconds=seconds,cpu_seconds=cpu,
        costs=dict(expert_packets=sum(r['expert_packets'] for r in records),input_chars=sum(r['expert_input_chars'] for r in records),
            output_chars=sum(r['expert_output_chars'] for r in records),actual_tokens=None,actual_usd=None),
        continuation_gate=complete and budget_pass and teachers['passed'] and proof['pass'] and any(p['sign']>0 for p in pairs) and all(p['sign']>=0 for p in pairs),
        default_promotion=False)
    print(json.dumps({k:result[k] for k in ('complete','budget_pass','pairs','costs','continuation_gate','seconds')}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','evaluate']);p.add_argument('--plan',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E165'};write(a.output,plan(v) if a.mode=='plan' else evaluate(v,a.plan,a.output))
