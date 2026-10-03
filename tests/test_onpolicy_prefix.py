"""Synthetic boundary and gradient-provenance checks; not game strength evidence."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
import torch
from rsi.ppo import ActorCritic,HP,advantages,update
from rsi.phase_rl import controller,extend_model
from rsi.run_env import battle_transition
from scripts.pilot_onpolicy_e146 import CONFIG,behavior_parity,reward


class OnPolicyPrefixTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(146)

    def test_pending_rewards_do_not_end_prefix(self):
        alive={'player':{'hp':10,'max_hp':80}}
        for d in ('card_reward','potion_reward','card_select'):
            self.assertFalse(battle_transition({**alive,'decision':d},6,6))
        self.assertTrue(battle_transition({**alive,'decision':'map_select'},6,6))
        self.assertFalse(battle_transition({**alive,'decision':'map_select'},6,5))
        self.assertFalse(battle_transition({**alive,'decision':'combat_play'},None,7))
        with self.assertRaises(ValueError):battle_transition({**alive,'decision':'combat_play'},6,6)
        with self.assertRaises(ValueError):battle_transition({**alive,'decision':'map_select'},6,7)
        self.assertFalse(battle_transition({'decision':'game_over','victory':False},6,6))

    def test_censors_have_no_reward_and_hp_is_not_changed(self):
        for s in ('timeout','action_cap','error','act_clear','victory'):
            with self.assertRaises(ValueError):reward({'status':s})
        record={'status':'curriculum_clear','final_hp':40,'final_max_hp':80};before=copy.deepcopy(record)
        self.assertEqual(reward(record),1.125);self.assertEqual(record,before)
        self.assertEqual(reward({'status':'defeat'}),-1.)

    def test_collection_parity_macro_credit_and_value_reset(self):
        model=extend_model(ActorCritic());state={'decision':'map_select','player':{'hp':80,'max_hp':80}}
        choices=[{'action':{'action':'select_map_node','args':{'col':i,'row':1}}} for i in range(3)]
        before=controller(model)(state,choices,None)[1]['probabilities']
        with torch.no_grad():model.value.weight.zero_();model.value.bias.zero_()
        after=controller(model)(state,choices,None)[1]['probabilities'];self.assertEqual(before,after)
        trajectory=[];choose=controller(model,146001,trajectory)
        for _ in range(4):choose(state,choices,None)
        self.assertEqual(behavior_parity(model,[trajectory])['transitions'],4)
        adv,returns=advantages([0.,0.,0.,1.125],[r['value'] for r in trajectory],gamma=1,lam=1)
        np.testing.assert_allclose(returns,np.full(4,1.125));self.assertGreater(adv[0],0)
        original=copy.deepcopy(HP);optimizer=torch.optim.Adam(model.parameters(),lr=CONFIG['lr'])
        with patch('rsi.ppo.advantages',wraps=advantages) as spy:
            metrics=update(model,optimizer,[(trajectory,1.125)],np.random.default_rng(146),hp={**CONFIG,'epochs':1})
            self.assertEqual(spy.call_args.kwargs['lam'],1.)
        self.assertEqual(HP,original);self.assertEqual(metrics['transitions'],4)
        with self.assertRaises(ValueError):controller(model,trajectory=[])
        with torch.no_grad():model.value.bias.add_(1.)
        with self.assertRaisesRegex(ValueError,'Behavior policy'):behavior_parity(model,[trajectory])
