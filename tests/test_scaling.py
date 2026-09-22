import unittest
from rsi.scaling import forecast,value
from rsi.planner import choose_plan
from rsi.policy import combat_candidates
class ScalingTests(unittest.TestCase):
 def test_boulder_damage_starts_next_turn_and_grows(self):
  f=forecast({'id':'ROLLING_BOULDER','stats':{'rollingboulderpower':10,'incrementamount':5}});self.assertEqual(f['current_damage'],0);self.assertEqual([r['unpowered_damage_each']for r in f['turns']],[10,15,20])
 def test_demon_form_strength_is_future_only(self):
  f=forecast({'id':'DEMON_FORM','stats':{'strengthpower':4}});self.assertEqual(f['current_strength'],0);self.assertEqual([r['strength']for r in f['turns']],[4,8,12])
 def test_remaining_hp_caps_future_value(self):
  self.assertEqual(value([forecast({'id':'ROLLING_BOULDER','stats':{'rollingboulderpower':10}})],{0:1}),.85)
 def test_unknown_not_given_effects(self):self.assertEqual(forecast({'id':'UNKNOWN'})['turns'],[])
 def test_demon_does_not_add_strength_to_same_turn_strike(self):
  s={'energy':4,'player':{'hp':80,'block':0},'enemies':[{'index':0,'hp':100,'block':0,'intents':[]}],'hand':[{'index':0,'id':'DEMON_FORM','name':'Demon Form','type':'Power','cost':3,'can_play':True,'target_type':'Self','stats':{'strengthpower':3}},{'index':1,'id':'STRIKE','name':'Strike','type':'Attack','cost':1,'can_play':True,'target_type':'AnyEnemy','damage_by_target':[{'target_index':0,'damage':6}]}]};_,f=choose_plan(s,combat_candidates(s),triggers=True,horizon=True);self.assertEqual(f['predicted_enemy_hp'][0],94);self.assertTrue(f['delayed_forecasts'])
 def test_survive_now_over_boulder(self):
  s={'energy':2,'player':{'hp':5,'block':0},'enemies':[{'index':0,'hp':100,'block':0,'intents':[{'damage':5}]}],'hand':[{'index':0,'id':'ROLLING_BOULDER','name':'Rolling Boulder','type':'Power','cost':2,'can_play':True,'target_type':'Self','stats':{'rollingboulderpower':10,'incrementamount':5}},{'index':1,'id':'DEFEND','name':'Defend','type':'Skill','cost':1,'can_play':True,'target_type':'Self','stats':{'block':5}}]};c,f=choose_plan(s,combat_candidates(s),triggers=True,horizon=True);self.assertEqual(c['action']['args']['card_index'],1);self.assertFalse(f['delayed_forecasts'])
