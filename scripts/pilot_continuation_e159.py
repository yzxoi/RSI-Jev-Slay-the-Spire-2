#!/usr/bin/env python3
"""Frozen 2x2 first-action/continuation diagnostic; no training or action search."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact, CONTROL
from rsi.continuation import FrozenProgram
from rsi.map_prefix import certified_snapshots
from rsi.root_teacher import rollout
from scripts.pilot_root_teacher_e149 import checked, info, cpu, parallel, version, same_runtime
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.evaluate_battle_search_e120 import audit, write

ARMS = ('actor_actor', 'selected_actor', 'actor_program', 'selected_program')
SOURCE = ROOT/'experiments/E149/evaluation-v3.json'
BANK = ROOT/'experiments/E149/bank-v1.json'
CERTIFICATE = ROOT/'experiments/E158/validation-v1.json'
CODE = ('rsi/continuation.py', 'rsi/root_teacher.py', 'rsi/map_prefix.py',
        'rsi/teacher.py', 'rsi/planner.py', 'rsi/policy.py', 'rsi/potions.py',
        'rsi/full.py', 'rsi/resources.py', 'rsi/ppo_actions.py', 'rsi/curriculum.py',
        'rsi/battle_search.py', 'rsi/numerical.py', 'rsi/retaliation.py')


def plan(v):
    source = checked(SOURCE, tracked=True)
    bank = checked(BANK, tracked=True)
    if not source['summary']['complete'] or not source['audit']['pass'] or not source['execution_parity']['passed']:
        raise ValueError('Incomplete source factorial cells')
    snapshots = certified_snapshots(info(CERTIFICATE), BANK, v)
    old = {r['case']: r for r in source['records']}
    roots = []
    for meta in bank['roots']:
        r = old[meta['case']]
        roots.append({k: meta[k] for k in ('index', 'case', 'seed', 'mode', 'ascension', 'raw')} |
            dict(first_actions={a:r[a+'_action'] for a in ('actor','selected')},
                 replay=meta['index'] in (0,1,10,11,20,21)))
    if len(roots) != 30 or len(snapshots) != 30:
        raise ValueError('Original roots missing')
    return dict(manifest=v, source=info(SOURCE), bank=info(BANK), restore_certificate=info(CERTIFICATE),
        checkpoint=checked(ROOT/'experiments/E149/plan-v3.json')['checkpoint'], roots=roots,
        arms=list(ARMS), arm_order='rotate by root index modulo4',
        program=dict(name=FrozenProgram.name, control=CONTROL, sources=[info(ROOT/p) for p in CODE],
            macro='cautious_macro: first reward/leave shop, cautious map, claim available potion',
            selection='complete_baseline, preserve triggering parent over interruptions'),
        budgets=dict(wall=600,cpu=1200,per_path=90,actions=2400,workers=4),
        bootstrap=dict(seed=159,repeats=10000,cluster='game_seed'),
        gate=dict(effect=.10,positive_seeds=3,lower95_strictly_positive=True,
                  nonnegative_difficulty_and_mode=True,no_lost_act2_or_victory=True),
        known_unsupported=['Crystal Sphere #64','Trial #294'],
        final_acceptance_seeds_unused=True, gradients=0)


def signature(r):
    return {k:r.get(k) for k in ('status','steps','transition_hash','final_hash')}


def summarize(records, p, proof, seconds, used):
    paths=[r['arms'][arm] for r in records for arm in ARMS]
    checks=[c for r in records for c in r['parity']]
    replays=[r['replay'] for r in records if 'replay' in r]
    complete=(len(records)==30 and len(paths)==120 and
        all(x['status'] in ('victory','defeat') and x.get('first_fight') is not None for x in paths))
    integrity=(complete and len(checks)==60 and all(x['exact'] for x in checks) and
        len(replays)==6 and all(x['exact'] for x in replays) and proof['pass'])
    out=dict(complete=complete,integrity=integrity,paths=len(paths),
        statuses=dict(Counter(x['status'] for x in paths)),
        actor_parity=dict(expected=60,compared=len(checks),matched=sum(c['exact'] for c in checks)),
        program_replays=dict(expected=6,completed=len(replays),matched=sum(x['exact'] for x in replays)),
        continuation_gate=False,final_acceptance_seeds_unused=True)
    if not complete:
        return out
    rows=[]
    for r in records:
        values={a:r['arms'][a]['first_fight']['utility'] for a in ARMS}
        rows.append({k:r[k] for k in ('case','seed','mode','ascension')} | dict(values=values,
            continuation_delta=values['actor_program']-values['actor_actor'],
            action_delta_actor=values['selected_actor']-values['actor_actor'],
            action_delta_program=values['selected_program']-values['actor_program'],
            interaction=values['selected_program']-values['actor_program']-
                        values['selected_actor']+values['actor_actor']))
    cluster=defaultdict(list)
    for r in rows:cluster[r['seed']].append(r['continuation_delta'])
    seed_delta=np.array([np.mean(x) for x in cluster.values()])
    rng=np.random.default_rng(p['bootstrap']['seed'])
    samples=seed_delta[rng.integers(len(seed_delta),size=(p['bootstrap']['repeats'],len(seed_delta)))].mean(axis=1)
    by_mode={m:float(np.mean([r['continuation_delta'] for r in rows if r['mode']==m])) for m in ('combat','prepare')}
    by_asc={str(a):float(np.mean([r['continuation_delta'] for r in rows if r['ascension']==a])) for a in (0,5,10)}
    counts={a:dict(first_clears=sum(r['arms'][a]['first_fight']['status']=='clear' for r in records),
                   act2=sum(2 in r['arms'][a]['acts_seen'] for r in records),
                   act3=sum(3 in r['arms'][a]['acts_seen'] for r in records),
                   victories=sum(r['arms'][a]['status']=='victory' for r in records)) for a in ARMS}
    no_lost=all((2 not in r['arms'][a+'_actor']['acts_seen'] or 2 in r['arms'][a+'_program']['acts_seen']) and
        (r['arms'][a+'_actor']['status']!='victory' or r['arms'][a+'_program']['status']=='victory')
        for r in records for a in ('actor','selected'))
    gates=dict(integrity=integrity,budget=seconds<=p['budgets']['wall'] and used<=p['budgets']['cpu'],
        effect=float(seed_delta.mean())>=p['gate']['effect'],lower_bound=float(np.quantile(samples,.025))>0,
        positive_seeds=int(sum(seed_delta>0))>=p['gate']['positive_seeds'],
        no_stratum_regression=all(v>=0 for v in [*by_mode.values(),*by_asc.values()]),
        no_lost_baseline_progress=no_lost)
    out.update(rows=rows,independent_game_seeds=len(cluster),positive_seeds=int(sum(seed_delta>0)),
        continuation_delta=float(seed_delta.mean()),cluster95=np.quantile(samples,[.025,.975]).tolist(),
        by_mode=by_mode,by_ascension=by_asc,counts=counts,
        mean_interaction=float(np.mean([r['interaction'] for r in rows])),
        gates=gates,continuation_gate=all(gates.values()))
    return out


def evaluate(v, path, output):
    p=checked(path,tracked=True);same_runtime(p,v)
    if p['arms']!=list(ARMS) or p['program']['name']!=FrozenProgram.name or p['program']['control']!=CONTROL:
        raise ValueError('Controller configuration changed')
    for item in p['program']['sources']:
        if info(ROOT/item['path'])!=item:raise ValueError('Frozen program code changed')
    source=checked(ROOT/p['source']['path'],p['source']['sha256'],tracked=True)
    checked(ROOT/p['bank']['path'],p['bank']['sha256'],tracked=True)
    snapshots=certified_snapshots(p['restore_certificate'],ROOT/p['bank']['path'],v)
    old={r['case']:r for r in source['records']}
    if [r['case'] for r in p['roots']]!=list(old):raise ValueError('Source cohort changed')
    model=load_phase(p['checkpoint'])
    directory=output.with_suffix('');directory.mkdir(parents=True,exist_ok=False)
    started, cpu_start=time.monotonic(),cpu();deadline=started+p['budgets']['wall']

    def one(meta):
        row={k:meta[k] for k in ('case','seed','mode','ascension')} | dict(arms={},parity=[])
        root=checked(ROOT/meta['raw']['path'],meta['raw']['sha256'])
        for a in ('actor','selected'):
            if meta['first_actions'][a]!=old[root['case']][a+'_action']:
                raise ValueError('Frozen first action changed')
        order=list(ARMS);offset=meta['index']%4;order=order[offset:]+order[:offset]
        for arm in order:
            first,controller=arm.split('_')
            if time.monotonic()>=deadline or cpu()-cpu_start>=p['budgets']['cpu']:
                row['arms'][arm]=dict(status='unstarted',error='Global budget exhausted')
                continue
            program=FrozenProgram(root['previous']) if controller=='program' else None
            result=rollout(root,v,model,arm,first_action=meta['first_actions'][first],full=True,
                snapshot=snapshots[root['case']],continuation=program,track_first_fight=True,
                seconds=min(p['budgets']['per_path'],deadline-time.monotonic()))
            row['arms'][arm]=compact(result)
            if controller=='actor':
                reference=old[root['case']]
                row['parity'].append(dict(arm=arm,full_exact=signature(result)==signature(reference['full'][first]),
                    first_fight_exact=signature(result.get('first_fight') or {})==signature(reference['greedy'][first])))
                row['parity'][-1]['exact']=all(row['parity'][-1][k] for k in ('full_exact','first_fight_exact'))
            if meta['replay'] and arm=='actor_program':
                if (result['status'] in ('victory','defeat') and time.monotonic()<deadline and
                        cpu()-cpu_start<p['budgets']['cpu']):
                    check=rollout(root,v,model,'replay:'+arm,full=True,expected=result['plan'],
                        snapshot=snapshots[root['case']],track_first_fight=True,
                        seconds=min(p['budgets']['per_path'],deadline-time.monotonic()))
                    row['replay']=dict(reference_arm=arm,result=compact(check),
                        exact=signature(check)==signature(result) and check['plan']==result['plan'] and
                            check.get('first_fight')==result.get('first_fight'))
                else:row['replay']=dict(reference_arm=arm,exact=False,reason='Reference/budget incomplete')
            write(directory/f"root-{meta['index']:02}.json",row)
        print(__import__('json').dumps(dict(case=row['case'],statuses={a:x['status'] for a,x in row['arms'].items()},
            first_clears={a:(x.get('first_fight') or {}).get('status') for a,x in row['arms'].items()})),flush=True)
        return row

    records=parallel(one,p['roots'],workers=p['budgets']['workers'])
    proof=audit(records);seconds=time.monotonic()-started;used=cpu()-cpu_start
    return dict(manifest=v,plan=info(path),records=records,audit=proof,seconds=seconds,cpu_seconds=used,
        summary=summarize(records,p,proof,seconds,used))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('plan','evaluate'))
    parser.add_argument('--plan',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Never overwrite an experiment attempt')
    torch.set_num_threads(1);v={**version(),'experiment':'E159','numpy':np.__version__}
    result=plan(v) if args.mode=='plan' else evaluate(v,args.plan,args.output)
    write(args.output,result)
    print(__import__('json').dumps({k:result[k] for k in ('summary','seconds','cpu_seconds','audit') if k in result}),flush=True)
