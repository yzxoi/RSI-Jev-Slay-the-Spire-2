import unittest
from rsi.planner import choose_plan
class ArtifactTests(unittest.TestCase):
 def test_artifact_prevents_false_bash_lethal(self):
  s={'energy':4,'player':{'hp':21,'block':0},'enemies':[{'index':0,'hp':52,'block':0,'intents':[{'total_damage':16}],'native_artifact':2}],'hand':[]};cs=[]
  for i,(name,cost,damage,block,vuln) in enumerate([('BASH',2,11,0,2),('PERFECTED_STRIKE',2,30,0,0),('STRIKE_IRONCLAD',1,12,0,0),('DEFEND',1,0,5,0)]):
   s['hand'].append({'index':i,'id':name,'cost':cost,'stats':{'block':block,'vulnerablepower':vuln},'damage_by_target':[{'target_index':0,'total_damage':damage}] if damage else []})
   cs.append({'id':str(i),'action':{'action':'play_card','card_index':i,**({'target_index':0} if damage else {})}})
  cs.append({'id':'end','action':{'action':'end_turn'}})
  _,p=choose_plan(s,cs);self.assertEqual(p['predicted_enemy_hp'][0],10);self.assertNotIn('0',p['plan_ids'])
  s['enemies'][0]['native_artifact']=0
  _,p=choose_plan(s,cs);self.assertEqual(p['predicted_enemy_hp'][0],0);self.assertIn('0',p['plan_ids'])
