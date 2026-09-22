import unittest
from rsi.triggers import gain_block,after_card,initial

def node(enemies=1):return {'block':0,'hp':{i:100 for i in range(enemies)},'eblock':{i:0 for i in range(enemies)},'used':frozenset({0}),'triggers':{'fnp':4,'juggernaut':8,'rage':0,'daughter':1,'soul':1,'uncertain_damage':0}}
class TriggerTests(unittest.TestCase):
 def test_two_independent_block_gains(self):
  n=node();gain_block(n,7);after_card(n,{'id':'IRON_WAVE','type':'Attack'},{});self.assertEqual(n['block'],8);self.assertEqual(n['hp'][0],84)
 def test_second_wind_counts_remaining_non_attacks_not_itself(self):
  n=node();c={'id':'SECOND_WIND','type':'Skill','stats':{'block':6}};cards={0:c,1:{'index':1,'type':'Curse'},2:{'index':2,'type':'Attack'},3:{'index':3,'type':'Skill'}};after_card(n,c,cards);self.assertEqual(n['block'],20);self.assertEqual(n['hp'][0],66);self.assertEqual(n['used'],{0,1,3})
 def test_empty_second_wind_has_no_flat_block(self):
  n=node();after_card(n,{'id':'SECOND_WIND','type':'Skill','stats':{'block':6}},{});self.assertEqual(n['block'],0)
 def test_random_target_not_claimed_as_single_enemy_damage(self):
  n=node(2);gain_block(n,5);self.assertEqual(n['hp'],{0:100,1:100});self.assertEqual(n['triggers']['uncertain_damage'],8)
 def test_rage_installs_before_following_attack(self):
  n=node();after_card(n,{'id':'RAGE','type':'Skill','stats':{'power':3}},{});self.assertEqual(n['block'],0);after_card(n,{'id':'STRIKE','type':'Attack'},{});self.assertEqual(n['block'],4);self.assertEqual(n['hp'][0],84)
 def test_dead_targets_do_not_receive_additional_trigger_damage(self):
  n=node();n['hp'][0]=5;gain_block(n,7);gain_block(n,1);self.assertEqual(n['hp'][0],0);self.assertEqual(n['block'],8)
