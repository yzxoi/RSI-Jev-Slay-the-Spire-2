"""Synthetic PUCT invariants, not game-strength evidence."""
import unittest
from unittest.mock import patch
try:
 import torch
 import numpy as np
except ImportError as exc:raise unittest.SkipTest('Optional neural search dependencies missing')from exc
from rsi.neural_search import Edge,Node,PUCT,normalized,SearchPolicy

class PUCTTests(unittest.TestCase):
 def test_expired_parent_budget_prevents_any_engine_probe(self):
  policy=SearchPolicy({}, {}, None, 'value', battle_deadline=10)
  choice={'action':{'action':'end_turn','args':{}}}
  state={'decision':'combat_play','round':1,'player':{'hp':1,'max_hp':80}}
  with patch.object(policy,'infer',return_value=([choice],np.array([1.]),0.)), \
       patch.object(policy,'probe') as probe, patch('rsi.neural_search.time.monotonic',return_value=11):
   with self.assertRaises(TimeoutError):policy(state,[choice],None,[])
   probe.assert_not_called()
 def test_parent_budget_reaches_every_root(self):
  policy=SearchPolicy({}, {}, None, 'value', battle_deadline=240)
  self.assertEqual(policy.root_deadline(200),240)
  self.assertEqual(policy.root_deadline(10),70)
  self.assertEqual(policy.root_deadline(245),240)
 def test_single_player_delayed_reward_and_visits(self):
  root=Node({},None,.5,[Edge({'name':'bad'},.8),Edge({'name':'delayed'},.2)])
  def expand(path):
   if path[0].choice['name']=='bad':return Node({},None,0.,terminal=True)
   if len(path)==1:return Node({},None,.9,[Edge({'name':'finish'},1.)])
   return Node({},None,1.,terminal=True)
  tree=PUCT(root,expand)
  for _ in range(64):tree.simulate()
  self.assertEqual(tree.selected()['name'],'delayed')
  self.assertEqual(sum(e.visits for e in root.edges),64)
  self.assertGreater(root.edges[1].total/root.edges[1].visits,.9)
  self.assertEqual(tree.maximum_depth,2)
  self.assertGreater(tree.cache_hits,0)
 def test_depth_cap_and_nonmerged_paths(self):
  root=Node({'same':1},None,.5,[Edge({'i':0},.5),Edge({'i':1},.5)])
  calls=[]
  def expand(path):
   calls.append(path)
   return Node({'same':1},None,.5,[Edge({'i':2},1.)])
  tree=PUCT(root,expand,max_depth=2)
  for _ in range(30):tree.simulate()
  self.assertEqual(tree.maximum_depth,2)
  self.assertIsNot(root.edges[0].child,root.edges[1].child)
  self.assertEqual(len(calls),4)
 def test_value_scale_and_nonfinite(self):
  self.assertEqual(normalized(-1),0);self.assertEqual(normalized(1.25),1)
  self.assertEqual(normalized(100),1)
  with self.assertRaises(ValueError):normalized(float('nan'))
if __name__=='__main__':unittest.main()
