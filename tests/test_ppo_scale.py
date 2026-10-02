"""Meaningful optional checks for E127 capacity/greedy-control changes."""
import unittest
try:
 import numpy as np
 import torch
except ImportError as exc: raise unittest.SkipTest('Optional PPO dependencies missing') from exc
from rsi.ppo import ActorCritic,padded,STATE_DIM,ACTION_DIM
from scripts.scale_ppo_e127 import attack_priority
from unittest.mock import patch

class ScaleTests(unittest.TestCase):
 def test_expanded_model_joint_gradients_and_checkpoint(self):
  torch.set_num_threads(1);m=ActorCritic(512,256)
  self.assertEqual(sum(p.numel() for p in m.parameters()),639234)
  s=np.ones(STATE_DIM,np.float32);a=np.ones((2,ACTION_DIM),np.float32);a[1]*=-1
  d,v=m(*padded([(s,a)]));(-d.log_prob(torch.tensor([0])).mean()+v.square().mean()).backward()
  for name,p in m.named_parameters():self.assertIsNotNone(p.grad,name);self.assertTrue(torch.isfinite(p.grad).all(),name)
  n=ActorCritic(**m.config);n.load_state_dict(m.state_dict());dn,vn=n(*padded([(s,a)]))
  torch.testing.assert_close(d.probs,dn.probs);torch.testing.assert_close(v,vn)
 def test_attack_priority_uses_card_order_then_lowest_target(self):
  def c(card,target):return {'action':{'action':'play_card','args':{'card_index':card,'target_index':target}}}
  end={'action':{'action':'end_turn','args':{}}}
  state={'decision':'combat_play','hand':[{'index':0,'type':'Skill'},{'index':1,'type':'Attack'},{'index':2,'type':'Attack'}],
         'enemies':[{'index':0,'hp':30},{'index':1,'hp':10}]}
  choices=[end,c(0,0),c(2,1),c(1,0),c(1,1)]
  with patch('scripts.scale_ppo_e127.baseline_choice',return_value=end):
   self.assertEqual(attack_priority(state,choices,None,[])[0],c(1,1))
if __name__=='__main__':unittest.main()
