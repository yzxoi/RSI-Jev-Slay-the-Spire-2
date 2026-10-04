#!/usr/bin/env python3
"""Eight fresh full natural run pairs, fixed program macro, no expert calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.campaign_teacher import episode,TeacherBudget
from rsi.potion_program import PotionProgram
from rsi.run_env import replay
from scripts.evaluate_battle_search_e120 import write,audit
from scripts.pilot_root_teacher_e149 import version,info,checked,same_runtime


def plan(v):
    source=ROOT/'experiments/E168/evaluation-v1.json';assert checked(source)['local_gate']
    return dict(manifest=v,prerequisite=info(source),cases=[dict(case=f'A{a}-{i:03}',
        seed=f'e170_potions_Ironclad_A{a}_{i:03}',character='Ironclad',ascension=a) for a in (0,5) for i in range(4)],
        arms=['typed','combined'],budgets=dict(actions=2400,run_seconds=120,replay_seconds=120,wall_seconds=600,workers=4),
        policy_sources=[info(ROOT/f) for f in ['rsi/campaign_teacher.py','rsi/potion_program.py','rsi/potion_applicability.py',
            'rsi/selection_semantics.py','rsi/teacher.py','rsi/continuation.py']],
        scope='New-seed autonomous program macro screen; not Astra hybrid acceptance',
        gate='All genuine terminals, exact replays, no illegal action; no negative (victory,completed acts,cleared fights) pair, >=2 positive pairs, >=4 seeds expose guarded potions.')


def usage(r):
    exposed=set();deferred=set();uses=[]
    for event in map(json.loads,(ROOT/r['trace_path']).read_text().splitlines()):
        if event['kind']!='decision':continue
        d=event['data'];s=d['state']
        if s.get('decision')=='combat_play':
            exposed.update(p['id'] for p in s['player']['potions'] if p.get('can_use') is not False
                and p['id'] in ('BLOCK_POTION','REGEN_POTION','SNECKO_OIL','ASHWATER'))
        deferred.update(x['reason'] for x in d.get('potion_applicability',[]) if x['reason'])
        if d['chosen']['action']['action']=='use_potion':uses.append(d['chosen']['details']['id'])
    return dict(guarded_potions_exposed=sorted(exposed),defer_reasons=sorted(deferred),potion_uses=uses)


def evaluate(v,path,output):
    p=checked(path,tracked=True);same_runtime(p,v);checked(ROOT/p['prerequisite']['path'],p['prerequisite']['sha256'])
    for source in p['policy_sources']:assert info(ROOT/source['path'])==source
    started=time.monotonic();deadline=started+600;budget=TeacherBudget(0)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    def one(item):
        config,arm=item
        r=episode({**config,'arm':'program_campaign','potion_arm':arm},v,budget,
            ROOT/'artifacts/runs/e170-unused-pending',deadline,
            program=PotionProgram(None,applicability=arm=='combined',typed_ashwater=True))
        r['verification']=replay(r,v,seconds=max(.001,min(120,deadline-time.monotonic())))
        r['potion_usage']=usage(r)
        write(directory/(config['case']+'-'+arm+'.json'),r)
        print(json.dumps({k:r.get(k) for k in ('case','potion_arm','status','final_context','completed_battles','completed_acts','error','potion_usage')}),flush=True)
        return r
    with ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(one,[(c,arm) for c in p['cases'] for arm in p['arms']]))
    progress=lambda r:(int(r['status']=='victory'),r['completed_acts'],r['completed_battles'])
    rows=[]
    for case in p['cases']:
        b,t=[next(r for r in records if r['case']==case['case'] and r['potion_arm']==arm) for arm in p['arms']]
        rows.append(dict(case=case['case'],seed=case['seed'],baseline=progress(b),treatment=progress(t),
            sign=(progress(t)>progress(b))-(progress(t)<progress(b)),
            exposed=bool(b['potion_usage']['guarded_potions_exposed'] or t['potion_usage']['guarded_potions_exposed']),
            transition_equal=b['transition_hash']==t['transition_hash']))
    proof=audit(records);seconds=time.monotonic()-started
    integrity=(all(r['status'] in ('victory','defeat') and r['verification']['status']=='match'
        and r['verification']['final_hash']==r['final_hash'] and r['illegal_actions']==0
        and r['expert_packets']==0 and r['compute_seconds']<=120 for r in records) and proof['pass'] and seconds<=600)
    return dict(manifest=v,plan=info(path),records=records,pairs=rows,raw_audit=proof,seconds=seconds,
        integrity_pass=integrity,screen_gate=integrity and all(r['sign']>=0 for r in rows)
            and sum(r['sign']>0 for r in rows)>=2 and sum(r['exposed'] for r in rows)>=4,
        model_api_calls=0,expert_decisions=0,default_promotion=False,
        scope=p['scope'])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['plan','evaluate']);ap.add_argument('--plan',type=Path)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('Never overwrite evidence')
    v={**version(),'experiment':'E170'}
    result=plan(v) if a.mode=='plan' else evaluate(v,a.plan,a.output)
    write(a.output,result)
    if a.mode=='evaluate':print(json.dumps({k:result[k] for k in ('integrity_pass','screen_gate','seconds','pairs')}))
