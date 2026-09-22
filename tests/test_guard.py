import unittest
from rsi.guard import filter_end_turn
class Guard(unittest.TestCase):
 def test_block_and_attack_improvement_and_retaliation(self):
  s={'energy':1,'hand':[{'index':0,'id':'CARD.DEFEND_IRONCLAD','cost':1,'stats':{'block':5}}],'player':{'hp':5,'block':0},'enemies':[{'index':0,'hp':10,'intents':[{'damage':7}]}]}
  cs=[{'id':'a0','action':{'action':'play_card','args':{'card_index':0}}},{'id':'a1','action':{'action':'end_turn'}}]
  self.assertEqual(len(filter_end_turn(s,cs)[0]),1)
  s['enemies'][0]['powers']=[{'name':'Enrage','amount':2}]
  self.assertEqual(len(filter_end_turn(s,cs)[0]),2)
  s['enemies'][0]['powers']=[];s['player']['block']=8
  self.assertEqual(len(filter_end_turn(s,cs)[0]),2)
 def test_energy_retention(self):
  s={'energy':1,'hand':[],'player':{'relics':[{'name':'Ice Cream'}]},'enemies':[]}
  self.assertFalse(filter_end_turn(s,[])[1]['excluded'])
