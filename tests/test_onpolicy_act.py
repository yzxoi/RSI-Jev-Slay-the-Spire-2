import unittest
import numpy as np
import torch
from rsi.run_env import act_transition,run_outcome
from rsi.ppo import ActorCritic
from rsi.phase_rl import controller,extend_model

class ActBoundaryTests(unittest.TestCase):
    def test_only_true_crossing_is_positive(self):
        for d in ('card_reward','potion_reward','map_select'):
            s={'decision':d,'context':{'act':1,'room_type':'Boss'},'player':{'hp':1}}
            self.assertFalse(act_transition(s,1,True))
        valid={'decision':'map_select','context':{'act':2,'room_type':'Map'},'player':{'hp':80}}
        self.assertTrue(act_transition(valid,1,True));self.assertIsNone(run_outcome(valid))
        self.assertFalse(act_transition(valid,None,False))
        with self.assertRaises(ValueError):act_transition(valid,1,False)
        with self.assertRaises(ValueError):act_transition({**valid,'decision':'combat_play'},1,True)
        with self.assertRaises(ValueError):act_transition({**valid,'player':{'hp':0}},1,True)
        with self.assertRaises(ValueError):act_transition({**valid,'context':{'act':3,'room_type':'Map'}},1,True)
        self.assertFalse(act_transition({'decision':'game_over','victory':False,'context':{'act':1}},1,True))

    def test_sample_stream_reproduction_and_probability(self):
        torch.set_num_threads(1);torch.manual_seed(145);model=extend_model(ActorCritic())
        state={'decision':'map_select','context':{'act':1,'floor':1},'player':{'hp':80,'max_hp':80}}
        choices=[{'action':{'action':'select_map_node','args':{'col':i,'row':1}}} for i in range(4)]
        a=controller(model,145001);b=controller(model,145001);greedy=controller(model)
        sequence=[]
        for _ in range(40):
            ca,pa=a(state,choices,None);cb,pb=b(state,choices,None)
            self.assertEqual(ca,cb);self.assertEqual(pa,pb);sequence.append(choices.index(ca))
            self.assertAlmostEqual(sum(pa['probabilities']),1.)
            self.assertAlmostEqual(pa['sampling_logprob'],np.log(pa['probabilities'][choices.index(ca)]))
            self.assertAlmostEqual(pa['sampling_logprob'],pa['old_logprob'],places=5)
        self.assertGreater(len(set(sequence)),1)
        cg,pg=greedy(state,choices,None)
        self.assertEqual(choices.index(cg),int(np.argmax(pg['probabilities'])))
