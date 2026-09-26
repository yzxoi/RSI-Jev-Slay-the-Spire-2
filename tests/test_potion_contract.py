import copy
import unittest
from rsi.potion_contract import PotionContract, identity
from rsi.policy import combat_candidates
from rsi.potions import with_potions
from rsi.trace import digest

class PotionContractTest(unittest.TestCase):
    def setUp(self):
        self.s={'context':{'floor':17},'decision':'combat_play','round':1,'hand':[],
                'player':{'hp':79,'max_hp':80,'potions':[{'index':0,'name':'Dex','vars':{'DexterityPower':2},'target_type':'AnyPlayer'},
                                                       {'index':1,'name':'Blood','vars':{'HealPercent':20},'target_type':'AnyPlayer'}]}}
        self.spec={'entry_hash':digest(self.s),'rules':[{'id':'dex','potion':identity(self.s['player']['potions'][0]),'when':'opening'},
             {'id':'blood','potion':identity(self.s['player']['potions'][1]),'when':'full_heal_deficit'}]}
    def choices(self,s):return with_potions(s,combat_candidates(s))
    def test_rebinds_compacted_slot_once_and_reserves_heal(self):
        pc=PotionContract(self.s,self.spec);c,_,e=pc.prepare(self.s,self.choices(self.s))
        after=copy.deepcopy(self.s);after['player']['potions'].pop(0);after['player']['potions'][0]['index']=0
        pc.accepted(e['rule_id'],self.s,after)
        c,allowed,_=pc.prepare(after,self.choices(after));self.assertIsNone(c);self.assertEqual(len(allowed),1)
        after['player']['hp']=64;c,_,e=pc.prepare(after,self.choices(after));self.assertEqual(c['action']['args']['potion_index'],0)
        with self.assertRaises(ValueError):pc.accepted('dex',self.s,after)
    def test_rejects_stale_ambiguous_and_unconfirmed(self):
        with self.assertRaises(ValueError):PotionContract({**self.s,'round':2},self.spec)
        pc=PotionContract(self.s,self.spec)
        with self.assertRaises(ValueError):pc.accepted('dex',self.s,self.s)
        broken=copy.deepcopy(self.s);broken['player']['potions'].append(broken['player']['potions'][0])
        with self.assertRaises(ValueError):pc.prepare(broken,self.choices(broken))
    def test_expiry_and_selection(self):
        pc=PotionContract(self.s,self.spec)
        with self.assertRaises(ValueError):pc.prepare({**self.s,'context':{'floor':18}},[])
        self.assertIsNone(pc.prepare({**self.s,'decision':'card_select'},[])[0])
