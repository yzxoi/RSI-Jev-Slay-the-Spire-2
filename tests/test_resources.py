import unittest
from rsi.full import macro_candidates
from rsi.potions import with_potions
from rsi.resources import legacy_projection, potion_decision


class ResourcesTests(unittest.TestCase):
    def test_automatic_and_currently_unusable_potions_are_excluded(self):
        state={'player':{'potions':[
            {'index':0,'name':'Fairy','usage':'Automatic','target_type':'Self'},
            {'index':1,'name':'Blocked','can_use':False,'target_type':'Self'},
            {'index':2,'name':'Fire','can_use':True,'target_type':'AnyEnemy'}]},
            'enemies':[{'index':3}]}
        self.assertEqual([c['action']['args'] for c in with_potions(state,[])],
                         [{'potion_index':2,'target_index':3}])

    def test_full_shop_needs_a_separate_discard_before_purchase(self):
        state={'decision':'shop','player':{'gold':100,'has_open_potion_slots':False,
               'potions':[{'index':1,'name':'Fairy','usage':'Automatic','can_discard':True}]},
               'potions':[{'index':0,'name':'Block','cost':50,'is_stocked':True,'can_buy':False}]}
        choices=macro_candidates(state,resource_decisions=True)
        self.assertEqual([c['action']['action'] for c in choices],['discard_potion','leave_room'])
        state['player']['has_open_potion_slots']=True
        state['potions'][0]['can_buy']=True
        self.assertEqual([c['action']['action'] for c in macro_candidates(state,resource_decisions=True)],
                         ['buy_potion','leave_room'])
        self.assertEqual([c['action']['action'] for c in macro_candidates(state)],['leave_room'])

    def test_full_reward_never_offers_claim(self):
        state={'decision':'potion_reward','can_claim':False,'can_skip':True,
               'potion':{'name':'Fire'},'player':{'has_open_potion_slots':False,
               'potions':[{'index':0,'name':'Fairy','usage':'Automatic','can_discard':True}]}}
        self.assertEqual([c['action']['action'] for c in macro_candidates(state,resource_decisions=True)],
                         ['skip_potion_reward','discard_potion'])

    def test_projection_only_removes_versioned_observations(self):
        state={'player':{'hp':42,'potion_capacity':2,'potions':[{'index':0,'name':'Fire','id':'FIRE_POTION','can_use':True}]}}
        self.assertEqual(legacy_projection(state),{'player':{'hp':42,'potions':[{'index':0,'name':'Fire'}]}})
        self.assertEqual(state['player']['potion_capacity'],2)

    def test_shared_question_keeps_inputs_and_reindexes_without_mutation(self):
        selected={'id':'a005','action':{'action':'end_turn'}}
        context,choices=potion_decision({'hp':5},'strategy',{'loss':6},selected,[])
        self.assertEqual(selected['id'],'a005')
        self.assertEqual(choices[0]['id'],'p000')
        self.assertEqual(context['plan'],{'loss':6})
