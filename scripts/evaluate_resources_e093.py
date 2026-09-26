"""Frozen five-character A10 resource integration smoke comparison."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import time
from rsi.engine import ROOT, CHARACTERS
from rsi.full import episode
from rsi.jev import Budget, Jev, MODEL
from rsi.matched import MatchedJev
from rsi.resources import legacy_projection
from rsi.trace import digest, version_manifest


def replay_responses(jev, source):
    """Re-use exact recorded requests, preserving source failures and cost records."""
    source_bytes=source.read_bytes();report=json.loads(source_bytes)
    for run in report['results']:
        data=(ROOT/run['trace_path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=run['trace_sha256']:raise RuntimeError('Source trace hash mismatch')
        request=response=None
        for row in map(json.loads,data.splitlines()):
            k,d=row['kind'],row['data']
            if k=='model_request':request=d;response=None
            elif k=='model_response':response=d
            elif k=='model_cache_store':
                if request is None or response is None:raise RuntimeError('Unbound recorded response')
                choices=[dict(value,id=ident) for ident,value in request['questions']['action']['criteria'].items()]
                if request['model']!=MODEL or digest({'model':MODEL,'state':request['state'],'candidates':choices})!=d['request_hash']:
                    raise RuntimeError('Recorded request hash mismatch')
                raw=response['response'];answer=raw['answers']['action']
                if answer['choice']!=d['choice']:raise RuntimeError('Recorded choice mismatch')
                jev.responses[d['request_hash']]={'choice':d['choice'],'source_trace':run['trace_path'],
                    'metadata':{'usage':raw['usage'],'seconds':response['seconds'],'answer':answer,'model':raw.get('model')}}
    return report,{'source_report':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
                   'preloaded_requests':len(jev.responses),'scope':'recorded responses are cached; wall time is not live API throughput'}


def transitions(run):
    rows=[json.loads(line) for line in (ROOT/run['trace_path']).read_text().splitlines()]
    result=[];before=choice=None
    for row in rows:
        if row['kind']=='before':before=row['data']['state_hash']
        elif row['kind']=='selected':choice=row['data']['action']
        elif row['kind']=='after':result.append((before,choice,row['data']['state_hash']))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--replay-from');parser.add_argument('--output',default='experiments/E093/smoke-result.json');args=parser.parse_args()
    if args.replay_from and args.output==args.replay_from:raise ValueError('Preserve the source report')
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before evaluation')
    configs=[{'character':c,'seed':f'e093_resources_{i:03}','ascension':10,'policy':policy,
              'max_steps':2000,'max_seconds':300}
             for i in (1,2) for c in CHARACTERS for policy in ('retaliate','retaliate_resources')]
    budget=Budget(3000,.75,conservative_failures=True);jev=MatchedJev(Jev(budget));source=replay=None
    if args.replay_from:source,replay=replay_responses(jev,ROOT/args.replay_from)
    start=time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda config:episode(config,manifest,jev),configs))
    for result in results:
        data=(ROOT/result['trace_path']).read_bytes();rows=[json.loads(line) for line in data.splitlines()]
        result['trace_verified']=hashlib.sha256(data).hexdigest()==result['trace_sha256']
        before=next(r['data']['state'] for r in rows if r['kind']=='before')
        result['initial_legacy_hash']=digest(legacy_projection(before))
        result['resource_actions']=dict(Counter(r['data']['action']['action'] for r in rows if r['kind']=='resource_transition'))
        result['model_seconds']=round(sum(r['data']['seconds'] for r in rows if r['kind']=='model_response'),3)
        result['resource_checks']=sum(r['kind']=='resource_check' for r in rows)
        result['models']=sorted(set(r['data']['response'].get('model','unknown') for r in rows if r['kind']=='model_response'))
        result['inventory_overflow']=any(len(r['data']['state'].get('player',{}).get('potions',[])) >
            r['data']['state'].get('player',{}).get('potion_capacity',999) for r in rows if r['kind'] in ('before','after'))
    pairs=[]
    for i in range(0,len(results),2):
        b,t=results[i:i+2]
        def progress(r):return (r['status']=='victory',r.get('act') or 0,r.get('floor') or 0)
        pairs.append({'character':b['character'],'seed':b['seed'],
                      'initial_legacy_parity':b['initial_legacy_hash']==t['initial_legacy_hash'],
                      'baseline':[b['status'],b.get('act'),b.get('floor')],
                      'treatment':[t['status'],t.get('act'),t.get('floor')],
                      'outcome':'error' if 'error' in (b['status'],t['status']) else
                      'better' if progress(t)>progress(b) else 'worse' if progress(t)<progress(b) else 'tie'})
    output={'experiment':'E093','scope':'compatibility smoke; not a strength promotion',
            'manifest':manifest,'configs':configs,'results':results,'pairs':pairs,
            'seconds':round(time.monotonic()-start,3),
            'budget':{'calls':budget.calls,'provider_reported_cost_usd':budget.spent-budget.estimated_usd,
                      'budgeted_spend_usd':budget.spent,'unknown_calls':budget.uncertain_calls}}
    if source:
        replay['trajectory_audit']=[]
        for prior,current in zip(source['results'],results):
            if any(prior[k]!=current[k] for k in ('character','seed','policy')):raise RuntimeError('Replay config mismatch')
            previous,now=transitions(prior),transitions(current)
            replay['trajectory_audit'].append({'character':prior['character'],'seed':prior['seed'],'policy':prior['policy'],
                'source_status':prior['status'],'prior_transitions':len(previous),'current_transitions':len(now),
                'prefix_identical':now[:len(previous)]==previous,
                'completed_trajectory_identical':now==previous if prior['status']!='error' else None})
        output['replay']=replay
    (ROOT/args.output).write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'statuses':dict(Counter(r['status'] for r in results)),
                      'pairs':dict(Counter(p['outcome'] for p in pairs)),
                      'budget':output['budget'],'seconds':output['seconds']}),flush=True)
    if any(r['status']=='error' or not r['trace_verified'] or r['inventory_overflow'] for r in results):raise SystemExit(1)
    if replay and any(not r['prefix_identical'] or r['completed_trajectory_identical'] is False for r in replay['trajectory_audit']):raise SystemExit(1)


if __name__=='__main__':main()
