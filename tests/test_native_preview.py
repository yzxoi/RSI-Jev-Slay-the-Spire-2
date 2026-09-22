import unittest
from rsi.live_plan import normalize
class Preview(unittest.TestCase):
 def test_owner_preview_and_calculated_damage(self):
  def card(i,ident,key,base,current):return {'index':i,'card_id':ident,'name':ident,'requires_target':True,'valid_target_indices':[0],'energy_cost':1,'playable':True,'target_type':'AnyEnemy','dynamic_values':[{'name':key,'base_value':base,'current_value':current}]}
  raw={'run':{'deck':[]},'combat':{'player':{'current_hp':20,'energy':3,'block':0,'powers':[{'power_id':'WEAK_POWER','amount':1},{'power_id':'DEXTERITY_POWER','amount':2}]},'enemies':[{'index':0,'current_hp':30,'block':0,'is_alive':True,'powers':[],'intents':[{'total_damage':None,'damage':None,'hits':None}]}],'hand':[card(0,'STRIKE_IRONCLAD','Damage',6,4),card(1,'PERFECTED_STRIKE','CalculatedDamage',6,18),card(2,'DEFEND_IRONCLAD','Block',5,7)]}}
  hand=normalize(raw)['hand'];self.assertEqual(hand[0]['damage_by_target'][0]['damage'],4);self.assertEqual(hand[1]['damage_by_target'][0]['damage'],18);self.assertEqual(hand[2]['stats']['block'],7)
