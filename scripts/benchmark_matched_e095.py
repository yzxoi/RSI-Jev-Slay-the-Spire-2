"""Fixed request throughput benchmark; no gameplay or win-rate inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from rsi.engine import ROOT
from rsi.jev import Jev, Budget
from rsi.matched import MatchedJev
from rsi.trace import Trace, digest, version_manifest


class SerialMatchedJev(MatchedJev):
    """Comparator with legacy global-call serialization, otherwise same cache."""
    def __init__(self,inner):
        super().__init__(inner);self.serial=threading.Lock()
    def choose(self,*args):
        with self.serial:return super().choose(*args)


def freeze(source):
    result=json.loads((source/'experiments/E093/smoke-result.json').read_text());items=[];seen=set()
    for run in result['results']:
        data=(source/run['trace_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==run['trace_sha256']
        for row in map(json.loads,data.splitlines()):
            if row['kind']!='model_request':continue
            body=row['data'];key=digest(body)
            if key in seen:continue
            seen.add(key);items.append({'state':body['state'],
                'candidates':[dict(value,id=ident) for ident,value in body['questions']['action']['criteria'].items()],
                'source_trace_sha256':run['trace_sha256'],'source_seq':row['seq']})
            if len(items)==8:break
        if len(items)==8:break
    data=json.dumps(items,sort_keys=True).encode()
    (ROOT/'artifacts/private/e095-requests.json').write_bytes(data)
    descriptor={'fixture_sha256':hashlib.sha256(data).hexdigest(),'unique_requests':8,
                'sources':[{k:x[k] for k in ('source_trace_sha256','source_seq')} for x in items]}
    (ROOT/'experiments/E095/fixture.json').write_text(json.dumps(descriptor,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-from',type=Path);a=p.parse_args()
    if a.freeze_from:return freeze(a.freeze_from)
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit before benchmarking')
    data=(ROOT/'artifacts/private/e095-requests.json').read_bytes();fixture=json.loads((ROOT/'experiments/E095/fixture.json').read_text())
    assert hashlib.sha256(data).hexdigest()==fixture['fixture_sha256']
    items=json.loads(data);jobs=items+items[:2];budget=Budget(30,.10,conservative_failures=True);arms=[]
    for name,cls in [('serial',SerialMatchedJev),('parallel',MatchedJev)]:
        jev=cls(Jev(budget));start=time.monotonic()
        def call(job):
            trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'experiment':'E095','scope':'request_benchmark','arm':name,'fixture_sha256':fixture['fixture_sha256']})
            r={'status':'error','source_seq':job['source_seq'],'source_trace_sha256':job['source_trace_sha256']}
            try:
                choice,meta=jev.choose(job['state'],job['candidates'],trace)
                r.update(status='ok',choice=choice['id'],cache_hit=meta.get('cache_hit',False),cost=meta['usage'].get('cost'),model=meta.get('model'))
            except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
            trace.write('summary',r);r['trace_path']=str(trace.path.relative_to(ROOT));r['trace_sha256']=trace.close()
            r['trace_verified']=hashlib.sha256(trace.path.read_bytes()).hexdigest()==r['trace_sha256'];return r
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(call,jobs))
        arm={'name':name,'seconds':round(time.monotonic()-start,3),'results':results,
             'noncached':sum(not r.get('cache_hit',False) for r in results),'cache_hits':sum(r.get('cache_hit',False) for r in results)}
        arms.append(arm);print(json.dumps({k:v for k,v in arm.items() if k!='results'}),flush=True)
    out={'manifest':manifest,'fixture':fixture,'arms':arms,'budget':{'calls':budget.calls,'provider_reported_cost_usd':budget.spent-budget.estimated_usd,'unknown_calls':budget.uncertain_calls},'scope':'API throughput only; model responses not required to be identical across independent calls'}
    (ROOT/'experiments/E095/result.json').write_text(json.dumps(out,indent=2)+'\n')
    if any(r['status']!='ok' for arm in arms for r in arm['results']):raise SystemExit(1)


if __name__=='__main__':main()
