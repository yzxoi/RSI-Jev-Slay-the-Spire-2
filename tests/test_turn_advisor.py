import unittest
from rsi.turn_advisor import validate_packet

class TurnAdvisorTest(unittest.TestCase):
    def setUp(self):
        self.request={'run_id':'R','case':'silent','round':2,'state_hash':'fresh'}
        self.packet={**self.request,'goal':'Survive','guidance':'Use current legal choices; preserve a route to lethal.'}
    def test_accepts_advice_and_rejects_stale_turn_run_and_actions(self):
        validate_packet(self.packet,self.request)
        for change in [{'round':3},{'run_id':'S'},{'state_hash':'old'},{'actions':['a001']},{'guidance':'x'*1201}]:
            with self.assertRaises(ValueError):validate_packet({**self.packet,**change},self.request)
