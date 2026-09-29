import unittest
from rsi.decider_backend import Ledger, BackendStopped, parse_choice, request_body, JEV, DEEPSEEK
from scripts.evaluate_deciders_e113 import paired, position, boundary

class BackendTests(unittest.TestCase):
    def test_unknown_billing_stops_new_calls(self):
        ledger=Ledger(3,1);ledger.acquire(.1);ledger.settle(.1,None,False)
        self.assertEqual(ledger.snapshot()['unknown_reserved'],.1)
        with self.assertRaises(BackendStopped):ledger.acquire(.1)

    def test_concurrent_reservations_bound_budget(self):
        ledger=Ledger(3,.15);ledger.acquire(.1)
        with self.assertRaises(BackendStopped):ledger.acquire(.1)
        ledger.settle(.1,.01,True);ledger.acquire(.1)

    def test_no_wrong_model_or_truncated_choice(self):
        cs=[{'id':'a000'}]
        good={'model':DEEPSEEK,'choices':[{'finish_reason':'stop','message':{'content':'{"choice":"a000"}'}}]}
        self.assertEqual(parse_choice(DEEPSEEK,good,cs),cs[0])
        good['choices'][0]['finish_reason']='length'
        with self.assertRaises(ValueError):parse_choice(DEEPSEEK,good,cs)
        with self.assertRaises(ValueError):parse_choice(JEV,{'answers':{'action':{'choice':'other'}}},cs)

    def test_reasoning_and_same_candidates(self):
        cs=[{'id':'a1','name':'x'},{'id':'a2','name':'y'}]
        body=request_body(DEEPSEEK,{},cs)
        self.assertEqual(body['reasoning'],{'effort':'low','exclude':True})
        self.assertEqual(body['response_format']['json_schema']['schema']['properties']['choice']['enum'],['a1','a2'])

    def test_reward_from_potion_is_not_battle_win(self):
        self.assertIsNone(boundary({'decision':'card_reward','from_event':True}))
        self.assertEqual(boundary({'decision':'card_reward','gold_earned':20,'player':{'hp':3}}),'win')

    def test_error_not_gameplay_loss_and_hp_tie_band(self):
        a={'status':'win','final_hp':20};b={'status':'win','final_hp':22}
        self.assertEqual(paired(a,b,'combat'),'tie')
        self.assertEqual(paired(a,dict(b,final_hp=23),'combat'),'better')
        self.assertEqual(paired(a,dict(b,status='error'),'combat'),'invalid')

if __name__=='__main__':unittest.main()
