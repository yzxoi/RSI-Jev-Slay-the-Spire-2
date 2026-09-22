import unittest
from rsi.encounters import sandpit_rule
class SandpitTests(unittest.TestCase):
    def state(self, n, playable=True):
        return {"combat":{"enemies":[{"is_alive":True,"powers":[{"power_id":"SANDPIT_POWER","amount":n}]}],"hand":[{"index":3,"card_id":"FRANTIC_ESCAPE","playable":playable,"energy_cost":2},{"index":5,"card_id":"FRANTIC_ESCAPE","playable":playable,"energy_cost":1}]}}
    def test_survival_before_damage(self):
        choices=[{"action":{"action":"play_card","card_index":i}} for i in [0,3,5]]
        r=sandpit_rule(self.state(1),choices)
        self.assertEqual(r['selected']['action']['card_index'],5)
        self.assertFalse(r['requires_expert'])
    def test_no_legal_escape_escalates_only_at_expiry(self):
        self.assertTrue(sandpit_rule(self.state(1),[])['requires_expert'])
        self.assertFalse(sandpit_rule(self.state(2),[])['requires_expert'])
        self.assertIsNone(sandpit_rule(self.state(3),[]))
        self.assertIsNone(sandpit_rule({'combat':{'enemies':[]}},[]))
