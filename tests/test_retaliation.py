import unittest
from rsi.planner import choose_plan
from rsi.policy import combat_candidates

def state(block=0,hp=30,enemy_hp=100,hits=1,thorns=5):
 return {'energy':1,'player':{'hp':hp,'block':block},'enemies':[{'index':0,'hp':enemy_hp,'block':0,'powers':[{'name':'Thorns','amount':thorns}],'intents':[]}],'hand':[{'index':0,'id':'CARD.STRIKE_IRONCLAD','type':'Attack','can_play':True,'cost':1,'target_type':'AnyEnemy','damage_by_target':[{'target_index':0,'damage':6,'repeat':hits,'total_damage':6*hits}]}]}
def forecast(s,force=True):return choose_plan(s,combat_candidates(s),depth=1,triggers=True,retaliation=True,force_first=force)[1]
class RetaliationTests(unittest.TestCase):
 def test_block_absorbs_retaliation(self):
  f=forecast(state(block=8));self.assertEqual((f['predicted_block'],f['predicted_self_loss']),(3,0))
 def test_excess_retaliation_costs_hp(self):
  f=forecast(state(block=2));self.assertEqual((f['predicted_block'],f['predicted_self_loss']),(0,3))
 def test_multi_hit_consumes_block_per_hit(self):
  f=forecast(state(block=11,hits=3));self.assertEqual((f['predicted_block'],f['predicted_self_loss'],f['predicted_enemy_hp'][0]),(0,4,82))
 def test_killing_hit_still_retaliates_but_no_later_hits(self):
  f=forecast(state(enemy_hp=6,hits=3));self.assertEqual((f['predicted_self_loss'],f['predicted_enemy_hp'][0]),(5,0))
 def test_lethal_retaliation_is_not_a_winning_plan(self):
  s=state(hp=5,enemy_hp=6);f=forecast(s,False);self.assertEqual(f['plan_ids'],[])
 def test_power_damage_avoids_thorns(self):
  s=state();s['player']['powers']=[{'name':'Juggernaut','amount':8}];s['hand']=[{'index':0,'id':'CARD.DEFEND_IRONCLAD','type':'Skill','cost':1,'can_play':True,'target_type':'Self','stats':{'block':5}}];f=forecast(s);self.assertEqual((f['predicted_self_loss'],f['predicted_block'],f['predicted_enemy_hp'][0]),(0,5,92))
 def test_no_thorns_control(self):
  f=forecast(state(thorns=0,block=8));self.assertEqual((f['predicted_self_loss'],f['predicted_block']),(0,8))
 def test_block_before_attack_is_preferred_when_it_prevents_death(self):
  s=state(hp=4,enemy_hp=6);s['energy']=2;s['hand'].append({'index':1,'id':'CARD.DEFEND_IRONCLAD','type':'Skill','cost':1,'can_play':True,'target_type':'Self','stats':{'block':5}});c,f=choose_plan(s,combat_candidates(s),triggers=True,retaliation=True);self.assertEqual(c['action']['args']['card_index'],1);self.assertEqual(f['predicted_self_loss'],0)
