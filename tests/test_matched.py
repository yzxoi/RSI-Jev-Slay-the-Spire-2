import unittest
import threading
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
 def test_independent_requests_overlap(self):
  barrier=threading.Barrier(3)
  class Blocking(Fake):
   def choose(self,s,cs,t):
    barrier.wait(timeout=5)
    return super().choose(s,cs,t)
  j=MatchedJev(Blocking());cs=[{'id':'a'}]
  with ThreadPoolExecutor(max_workers=2) as pool:
   calls=[pool.submit(j.choose,{'state':i},cs,Trace()) for i in range(2)]
   barrier.wait(timeout=5)
   self.assertEqual([f.result(timeout=5)[0] for f in calls],[cs[0],cs[0]])

 def test_failure_reaches_waiters_and_does_not_poison_retry(self):
  started=threading.Event();release=threading.Event();waiting=threading.Event()
  class FailsOnce(Fake):
   def choose(self,s,cs,t):
    self.calls+=1
    if self.calls==1:
     started.set()
     if not release.wait(5):raise AssertionError('release deadline')
     raise RuntimeError('fixture failure')
    return cs[0],{'usage':{'cost':.01},'answer':{'choice':cs[0]['id']},'model':'fixture'}
  class WaitTrace(Trace):
   def write(self,k,v):
    super().write(k,v)
    if k=='model_cache_wait':waiting.set()
  fake=FailsOnce();j=MatchedJev(fake);cs=[{'id':'a'}]
  with ThreadPoolExecutor(max_workers=2) as pool:
   owner=pool.submit(j.choose,{'s':1},cs,Trace());self.assertTrue(started.wait(5))
   waiter=pool.submit(j.choose,{'s':1},cs,WaitTrace())
   try:self.assertTrue(waiting.wait(5))
   finally:release.set()
   for f in (owner,waiter):
    with self.assertRaisesRegex(RuntimeError,'fixture failure'):f.result(timeout=5)
  self.assertEqual(fake.calls,1)
  self.assertEqual(j.choose({'s':1},cs,Trace())[0],cs[0]);self.assertEqual(fake.calls,2)

 def test_cached_metadata_is_not_mutated_by_callers(self):
  j=MatchedJev(Fake());cs=[{'id':'a'}]
  _,first=j.choose({},cs,Trace());first['answer']['choice']='bad'
  _,cached=j.choose({},cs,Trace());self.assertEqual(cached['answer']['choice'],'a')
  cached['answer']['choice']='bad'
  self.assertEqual(j.choose({},cs,Trace())[1]['answer']['choice'],'a')

 def test_concurrent_identical_and_treatment(self):
  f=Fake();j=MatchedJev(f);cs=[{'id':'a','action':{'action':'end_turn'}}]
  with ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(lambda _:j.choose({'hp':10},cs,Trace()),range(8)))
  self.assertEqual(f.calls,1);self.assertEqual(sum(m['usage']['cost'] for c,m in out),.01);self.assertEqual(sum(m.get('cache_hit',False) for c,m in out),7)
  j.choose({'hp':10,'advice':'treatment'},cs,Trace());self.assertEqual(f.calls,2)
  t=Trace();current=[dict(cs[0])];chosen,m=j.choose({'hp':10},current,t);self.assertIs(chosen,current[0]);self.assertEqual(t.rows[0][1]['source_trace'],'fixture.jsonl')
