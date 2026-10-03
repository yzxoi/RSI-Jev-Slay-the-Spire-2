import unittest
import numpy as np
import torch
from rsi.ppo import ActorCritic,encode,padded
from rsi.phase_rl import phase_encode,extend_model,awr_weights


class PhaseEncodingTests(unittest.TestCase):
    def setUp(self):
        self.state={'decision':'map_select','context':{'act':1,'floor':2,'boss':{'id':'A'}},'player':{'hp':40,'max_hp':80,'gold':99}}
        self.choices=[{'action':{'action':'select_map_node','args':{'col':0,'row':3}},'details':{'type':'Monster'}}]

    def test_global_state_alias_is_removed(self):
        other={**self.state,'context':{'act':3,'floor':16,'boss':{'id':'B'}}}
        np.testing.assert_array_equal(encode(self.state,self.choices)[0],encode(other,self.choices)[0])
        self.assertFalse(np.array_equal(phase_encode(self.state,self.choices)[0],phase_encode(other,self.choices)[0]))

    def test_warm_extension_preserves_old_outputs(self):
        torch.manual_seed(11);old=ActorCritic();new=extend_model(old)
        choices=self.choices+[{'action':{'action':'select_map_node','args':{'col':1,'row':3}},'details':{'type':'Elite'}}]
        a,v=old(*padded([encode(self.state,choices)]));b,w=new(*padded([phase_encode(self.state,choices)]))
        torch.testing.assert_close(a.probs,b.probs,atol=1e-6,rtol=1e-6);torch.testing.assert_close(v,w,atol=1e-6,rtol=1e-6)

    def test_awr_detaches_baseline_and_favours_larger_advantage(self):
        v=torch.tensor([.1,.1],requires_grad=True);w=awr_weights(torch.tensor([-1.,1.]),v)
        self.assertFalse(w.requires_grad);self.assertGreater(w[1],w[0]);self.assertAlmostEqual(float(w.mean()),1.)

    def test_training_split_boundary(self):
        from scripts.pilot_fullpolicy_e140 import require_train
        for record in ({'case':'test-000'},{'case':'val-000'},{'case':'train-000','split':'dev'}):
            with self.assertRaises(ValueError):require_train(record)
        require_train({'case':'train-000','split':'train'})
