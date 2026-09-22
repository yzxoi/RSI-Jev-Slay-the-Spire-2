import copy
import unittest
from rsi.rescue import rescue_choice
from rsi.policy import combat_candidates

def state():
 return {'energy':0,'hand':[],'player':{'hp':4,'block':19,'potions':[{'index':2,'name':'Block Potion','vars':{'Block':12},'target_type':'AnyPlayer'}]},'enemies':[{'index':0,'hp':100,'block':0,'intents':[{'damage':33}]}]}
class RescueTests(unittest.TestCase):
 def test_block_potion_uses_actual_slot_to_avoid_predicted_lethal(self):
  s=state();c,r=rescue_choice(s,combat_candidates(s));self.assertEqual(c['action']['args'],{'potion_index':2});self.assertEqual(r['override']['predicted_loss_after'],2);self.assertEqual(s['player']['block'],19)
 def test_no_potion_when_existing_plan_fully_covers(self):
  s=state();s['player']['block']=40;c,r=rescue_choice(s,combat_candidates(s));self.assertEqual(c['action']['action'],'end_turn');self.assertIsNone(r['override'])
 def test_missing_values_do_not_invent_block(self):
  s=state();s['player']['potions'][0]['vars']=None;c,r=rescue_choice(s,combat_candidates(s));self.assertEqual(r['forecasts'],[])
 def test_energy_enables_only_modeled_cards(self):
  s=state();s['player']['block']=0;s['enemies'][0]['intents']=[{'damage':5}];s['player']['potions']=[{'index':0,'name':'Energy Potion','vars':{'Energy':2},'target_type':'AnyPlayer'}];s['hand']=[{'index':0,'id':'CARD.DEFEND_IRONCLAD','name':'Defend','type':'Skill','cost':1,'stats':{'block':5},'target_type':'Self','can_play':False}]
  c,r=rescue_choice(s,combat_candidates(s));self.assertTrue(r['override']['avoids_predicted_lethal']);self.assertEqual(r['override']['effect']['unlocked_indices'],[0])
 def test_damage_potion_does_not_assume_invincible_kill(self):
  s=state();s['player']['potions']=[{'index':0,'name':'Fire Potion','vars':{'Damage':20},'target_type':'AnyEnemy'}];s['enemies'][0]['hp']=10;s['enemies'][0]['powers']=[{'name':'Invincible','amount':1}];_,r=rescue_choice(s,combat_candidates(s));self.assertEqual(r['forecasts'],[])
