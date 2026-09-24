import unittest

from rsi.numerical import weakened_intent_damage
from rsi.planner import choose_plan
from rsi.policy import combat_candidates


def combat(powers=None, intents=None, with_defend=False):
    hand=[{'index':0,'id':'NEUTRALIZE','name':'Neutralize','cost':0,'type':'Attack',
           'can_play':True,'target_type':'AnyEnemy','stats':{'weakpower':1},
           'damage_by_target':[{'target_index':0,'damage':2}]}]
    if with_defend:
        hand.append({'index':1,'id':'DEFEND','name':'Defend','cost':1,'type':'Skill',
                     'can_play':True,'target_type':'Self','stats':{'block':5}})
    return {'energy':1,'player':{'hp':50,'block':0},
            'enemies':[{'index':0,'hp':40,'block':0,'intents':intents or [{'type':'Attack','damage':20}],
                        'powers':powers or []}], 'hand':hand}


class WeakForecastTests(unittest.TestCase):
    def test_per_hit_rounding_matches_observed_multi_hit_transition(self):
        enemy={'intents':[{'type':'Attack','damage':7,'hits':2,'total_damage':14}]}
        self.assertEqual(weakened_intent_damage(enemy),10)

    def test_weak_opener_can_prevent_more_current_damage_than_defend(self):
        state=combat(with_defend=True)
        choices=combat_candidates(state)
        baseline,_=choose_plan(state,choices,triggers=True,retaliation=True)
        treatment,forecast=choose_plan(state,choices,triggers=True,retaliation=True,weak_forecast=True)
        self.assertEqual(baseline['name'],'Defend')
        self.assertEqual(treatment['name'],'Neutralize')
        self.assertEqual(forecast['predicted_total_hp_loss'],10)

    def test_existing_weak_or_artifact_does_not_double_count(self):
        for power in ('Weak','Artifact'):
            state=combat(powers=[{'name':power,'amount':1}])
            _,forecast=choose_plan(state,combat_candidates(state),force_first=True,weak_forecast=True)
            self.assertEqual(forecast['predicted_total_hp_loss'],20)
            self.assertEqual(forecast['forecast_new_weak'],[])

    def test_nonattacking_target_has_no_immediate_prevention(self):
        state=combat(intents=[{'type':'Buff'}])
        _,forecast=choose_plan(state,combat_candidates(state),force_first=True,weak_forecast=True)
        self.assertEqual(forecast['predicted_total_hp_loss'],0)

