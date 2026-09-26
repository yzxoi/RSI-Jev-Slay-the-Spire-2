import copy
import unittest
from rsi.lethal_certificate import nominate
from rsi.policy import combat_candidates

class LethalCertificateTest(unittest.TestCase):
    def state(self):
        return {'context':{'room_type':'Boss'},'decision':'combat_play','hand':[{'index':3,'id':'CARD.STRIKE_IRONCLAD','name':'Strike','can_play':True,'target_type':'AnyEnemy','damage_by_target':[{'target_index':2,'damage':16}]}],
                'enemies':[{'index':2,'name':'Leader','hp':12,'block':0,'powers':None}]}
    def test_simple_preview_only_nominates(self):
        s=self.state();self.assertEqual(len(nominate(s,combat_candidates(s))),1)
    def test_conditional_card_multiple_leaders_and_block_abstain(self):
        s=self.state();s['hand'][0]['id']='CARD.PACTS_END';self.assertEqual(nominate(s,combat_candidates(s)),[])
        s=self.state();s['enemies'][0]['block']=10;self.assertEqual(nominate(s,combat_candidates(s)),[])
        s=self.state();s['enemies'].append({'index':4,'hp':1,'powers':None});self.assertEqual(nominate(s,combat_candidates(s)),[])
    def test_opaque_effect_is_never_a_certificate_from_arithmetic(self):
        s=self.state();s['enemies'][0]['powers']=[{'name':'Revive','amount':1}]
        # Nomination is intentionally not a certificate: only probe() can certify.
        self.assertEqual(len(nominate(s,combat_candidates(s))),1)
        self.assertNotIn('certified',nominate(s,combat_candidates(s))[0])
