import unittest
from rsi.knowledge import retrieval, strategic_reasons

class GuidanceTests(unittest.TestCase):
    def test_no_named_archetype_without_evidence(self):
        s={'player':{'deck':[{'id':'CARD.STRIKE_IRONCLAD','type':'Attack','cost':1,'stats':{'damage':6}}]}}
        r=retrieval(s)
        self.assertEqual(r['mechanic_lessons'],[])
        self.assertEqual(r['deck_capabilities']['counts']['known_scaling_cards'],0)
        self.assertEqual(strategic_reasons(s),[])
    def test_native_and_headless_select_same_mechanic(self):
        a={'player':{'deck':[{'id':'CARD.FEEL_NO_PAIN','type':'Power','cost':1} ]},'player_powers':[{'name':'Juggernaut','amount':8}]}
        b={'screen':'COMBAT','run':{'deck':[{'card_id':'FEEL_NO_PAIN','card_type':'Power','energy_cost':1}]},'combat':{'player':{'powers':[{'power_id':'JUGGERNAUT_POWER','amount':8}]}}}
        self.assertEqual(retrieval(a),retrieval(b))
        self.assertIn('active_unmodeled_trigger',strategic_reasons(b))
    def test_unplayable_power_does_not_trigger_setup_request(self):
        s={'hand':[{'id':'CARD.DEMON_FORM','type':'Power','can_play':False}]}
        self.assertEqual(strategic_reasons(s),[])
        s['hand'][0]['can_play']=True
        self.assertEqual(strategic_reasons(s),['playable_setup'])
