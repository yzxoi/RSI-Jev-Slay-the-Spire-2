"""Preregistered E038 paired A0 development cohort."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rsi.full import episode
from rsi.jev import Jev,Budget
from rsi.matched import MatchedJev
from rsi.trace import version_manifest
manifest=version_manifest();assert not manifest['tracked_dirty'];budget=Budget(1200,3,conservative_failures=True);matched=MatchedJev(Jev(budget))
class PerRun:
 def __init__(self):self.calls=0;self.cost=0
 def choose(self,state,choices,trace):
  if self.calls>=200 or self.cost+Budget.reserve_usd>.5:raise RuntimeError('Per-run model budget exhausted')
  c,m=matched.choose(state,choices,trace);self.calls+=not m.get('cache_hit',False);self.cost+=m.get('usage',{}).get('cost',0);return c,m
configs=[dict(character='Ironclad',ascension=0,seed=f'a0_e038_dev_{i:03}',policy=p,max_steps=1500,max_seconds=300)for i in range(1,4)for p in ['triggered','retaliate']]
with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda c:episode(c,manifest,PerRun()),configs))
out={'manifest':manifest,'configs':configs,'results':results,'budget':{'requests':budget.calls,'cost_usd':budget.spent,'unknown':budget.unknown}}
Path('experiments/E038/development-v1.json').write_text(json.dumps(out,indent=2)+'\n')
