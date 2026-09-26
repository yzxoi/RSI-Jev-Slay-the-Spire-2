"""Frozen five-character A10 resource integration smoke comparison."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time
from rsi.engine import ROOT, CHARACTERS
from rsi.full import episode
from rsi.jev import Budget, Jev
from rsi.matched import MatchedJev
from rsi.resources import legacy_projection
from rsi.trace import digest, version_manifest


def main():
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before evaluation')
    configs=[{'character':c,'seed':f'e093_resources_{i:03}','ascension':10,'policy':policy,
              'max_steps':2000,'max_seconds':300}
             for i in (1,2) for c in CHARACTERS for policy in ('retaliate','retaliate_resources')]
    budget=Budget(3000,.75,conservative_failures=True);jev=MatchedJev(Jev(budget));start=time.monotonic()
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
    (ROOT/'experiments/E093/smoke-result.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'statuses':dict(Counter(r['status'] for r in results)),
                      'pairs':dict(Counter(p['outcome'] for p in pairs)),
                      'budget':output['budget'],'seconds':output['seconds']}),flush=True)
    if any(r['status']=='error' or not r['trace_verified'] or r['inventory_overflow'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
