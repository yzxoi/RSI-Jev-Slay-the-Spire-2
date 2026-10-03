import copy
import unittest
import numpy as np
import torch
from rsi.ppo import ActorCritic,padded
from rsi.phase_rl import extend_model as phase_model,phase_encode
from rsi.rich_observation import SCHEMA,rich_encode,extend_model

class RichObservationTests(unittest.TestCase):
    def setUp(self):
        self.state={'decision':'map_select','context':{'act':1,'floor':2},'player':{'hp':40,'max_hp':80},
            'learning':{'schema':SCHEMA,'piles':{'draw':[{'id':'A'},{'id':'B'}]},'orbs':[{'id':'LIGHTNING'},{'id':'DARK'}],
            'osty':{'hp':5,'alive':True},'map':{'rows':[[{'col':0,'row':4,'type':'Monster','children':[]}]]}}}
        self.choices=[{'action':{'action':'select_map_node','args':{'col':0,'row':3}}}]
    def test_information_alias_probes(self):
        # Synthetic state variations, not gameplay evidence.
        original=rich_encode(self.state,self.choices)[0]
        for change in ('draw','orbs','osty','map'):
            state=copy.deepcopy(self.state);e=state['learning']
            if change=='draw':e['piles']['draw'].reverse()
            elif change=='orbs':e['orbs'].reverse()
            elif change=='osty':e['osty']['hp']=9
            else:e['map']['rows'][0][0]['type']='RestSite'
            self.assertFalse(np.array_equal(original,rich_encode(state,self.choices)[0]),change)
            np.testing.assert_array_equal(phase_encode(self.state,self.choices)[0],phase_encode(state,self.choices)[0])
    def test_missing_schema_rejected(self):
        with self.assertRaises(ValueError):rich_encode({k:v for k,v in self.state.items() if k!='learning'},self.choices)
    def test_extension_preserves_frozen_model(self):
        torch.set_num_threads(1);torch.manual_seed(141)
        old=phase_model(ActorCritic());new=extend_model(old)
        choices=self.choices+[{'action':{'action':'select_map_node','args':{'col':1,'row':3}}}]
        p,v=old(*padded([phase_encode(self.state,choices)]));q,w=new(*padded([rich_encode(self.state,choices)]))
        torch.testing.assert_close(p.probs,q.probs,atol=1e-6,rtol=1e-6)
        torch.testing.assert_close(v,w,atol=1e-6,rtol=1e-6)
