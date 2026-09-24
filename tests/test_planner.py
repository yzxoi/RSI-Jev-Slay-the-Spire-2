import unittest
from rsi.policy import combat_candidates
from rsi.planner import choose_plan
class PlannerTests(unittest.TestCase):
    def test_hp_loss_weight_changes_a_real_damage_block_tradeoff(self):
        state={'energy':1,'player':{'hp':30,'block':0},
               'enemies':[{'index':0,'hp':50,'block':0,'intents':[{'damage':10}]}],
               'hand':[{'index':0,'id':'STRIKE','name':'Strike','cost':1,'type':'Attack',
                        'can_play':True,'target_type':'AnyEnemy',
                        'damage_by_target':[{'target_index':0,'damage':10}]},
                       {'index':1,'id':'DEFEND','name':'Defend','cost':1,'type':'Skill',
                        'can_play':True,'target_type':'Self','stats':{'block':5}}]}
        candidates=combat_candidates(state)
        baseline,baseline_plan=choose_plan(state,candidates)
        treatment,treatment_plan=choose_plan(state,candidates,hp_loss_weight=3.0)
        self.assertEqual(baseline['name'],'Strike')
        self.assertEqual(treatment['name'],'Defend')
        self.assertEqual((baseline_plan['predicted_total_hp_loss'],treatment_plan['predicted_total_hp_loss']),(10,5))
        state['enemies'][0]['hp']=10
        lethal,_=choose_plan(state,combat_candidates(state),hp_loss_weight=3.0)
        self.assertEqual(lethal['name'],'Strike')

    def test_combined_lethal_beats_defending(self):
        s={'energy':2,'player':{'hp':5,'block':0},'enemies':[{'index':0,'hp':12,'block':0,'intents':[{'damage':20}]}], 'hand':[]}
        for i in range(2):s['hand'].append({'index':i,'id':'STRIKE','name':'Strike','cost':1,'can_play':True,'target_type':'AnyEnemy','stats':{'damage':6},'damage_by_target':[{'target_index':0,'damage':6}]})
        s['hand'].append({'index':2,'id':'DEFEND','name':'Defend','cost':1,'can_play':True,'target_type':'Self','stats':{'block':5}})
        c,p=choose_plan(s,combat_candidates(s));self.assertEqual(c['name'],'Strike');self.assertEqual(p['predicted_enemy_hp'][0],0)
    def test_body_slam_follows_block(self):
        s={'energy':1,'player':{'hp':20,'block':0},'enemies':[{'index':0,'hp':5,'block':0,'intents':[{'damage':10}]}], 'hand':[{'index':0,'id':'BODY_SLAM','name':'Slam','cost':0,'can_play':True,'target_type':'AnyEnemy','stats':{'damage':0},'damage_by_target':[{'target_index':0,'damage':0}]},{'index':1,'id':'DEFEND','name':'Defend','cost':1,'can_play':True,'target_type':'Self','stats':{'block':5}}]}
        c,p=choose_plan(s,combat_candidates(s));self.assertEqual(c['name'],'Defend');self.assertEqual(p['predicted_enemy_hp'][0],0)
