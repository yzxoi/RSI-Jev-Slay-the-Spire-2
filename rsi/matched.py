"""Opt-in process-local memoization for matched decision experiments."""
import copy
import threading
from .trace import digest
from .jev import MODEL

class MatchedJev:
    def __init__(self, inner):
        self.inner=inner
        self.responses={}
        self.lock=threading.Lock()

    def choose(self,state,candidates,trace):
        request={'model':MODEL,'state':state,'candidates':candidates}
        key=digest(request)
        # Whole-call lock also makes concurrent identical requests single-flight.
        # This optional evaluation mode trades macro throughput for exact pairing.
        with self.lock:
            if key in self.responses:
                entry=self.responses[key]
                trace.write('model_cache_hit',{'request_hash':key,'request':request,**entry})
                selected=next(c for c in candidates if c['id']==entry['choice'])
                meta=copy.deepcopy(entry['metadata']);meta['usage']={'cost':0};meta['cache_hit']=True
                return selected,meta
            selected,meta=self.inner.choose(state,candidates,trace)
            self.responses[key]={'choice':selected['id'],'metadata':copy.deepcopy(meta),'source_trace':str(trace.path)}
            trace.write('model_cache_store',{'request_hash':key,'choice':selected['id']})
            return selected,meta
