import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from rsi.matched import MatchedJev
class Trace:
 path=Path('fixture.jsonl')
 def __init__(self):self.rows=[]
 def write(self,k,v):self.rows.append((k,v))
class Fake:
 def __init__(self):self.calls=0
 def choose(self,s,cs,t):
  self.calls+=1
  return cs[0],{'usage':{'cost':.01},'answer':{'choice':cs[0]['id']},'model':'fixture'}
class MatchedTests(unittest.TestCase):
 def test_concurrent_identical_and_treatment(self):
  f=Fake();j=MatchedJev(f);cs=[{'id':'a','action':{'action':'end_turn'}}]
  with ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(lambda _:j.choose({'hp':10},cs,Trace()),range(8)))
  self.assertEqual(f.calls,1);self.assertEqual(sum(m['usage']['cost'] for c,m in out),.01);self.assertEqual(sum(m.get('cache_hit',False) for c,m in out),7)
  j.choose({'hp':10,'advice':'treatment'},cs,Trace());self.assertEqual(f.calls,2)
  t=Trace();current=[dict(cs[0])];chosen,m=j.choose({'hp':10},current,t);self.assertIs(chosen,current[0]);self.assertEqual(t.rows[0][1]['source_trace'],'fixture.jsonl')
