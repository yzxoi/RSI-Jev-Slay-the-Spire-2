"""Opt-in process-local memoization for matched decision experiments."""
import copy
from concurrent.futures import Future
import threading
from .trace import digest
from .jev import MODEL

class MatchedJev:
    def __init__(self, inner):
        self.inner=inner
        self.responses={}
        self.pending={}
        self.lock=threading.Lock()

    def choose(self,state,candidates,trace):
        request={'model':MODEL,'state':state,'candidates':candidates}
        key=digest(request)
        with self.lock:
            entry=self.responses.get(key)
            future=self.pending.get(key)
            owner=entry is None and future is None
            if owner:
                future=Future();self.pending[key]=future
        if not owner:
            if entry is None:
                trace.write('model_cache_wait',{'request_hash':key})
                entry=future.result()
            trace.write('model_cache_hit',{'request_hash':key,'request':request,**entry})
            selected=next(c for c in candidates if c['id']==entry['choice'])
            meta=copy.deepcopy(entry['metadata']);meta['usage']={'cost':0};meta['cache_hit']=True
            return selected,meta
        try:
            selected,meta=self.inner.choose(state,candidates,trace)
            entry={'choice':selected['id'],'metadata':copy.deepcopy(meta),'source_trace':str(trace.path)}
            trace.write('model_cache_store',{'request_hash':key,'choice':selected['id']})
            with self.lock:
                self.responses[key]=entry
                self.pending.pop(key)
                future.set_result(entry)
            return selected,meta
        except BaseException as exc:
            with self.lock:
                self.pending.pop(key,None)
                if not future.done():future.set_exception(exc)
            raise
