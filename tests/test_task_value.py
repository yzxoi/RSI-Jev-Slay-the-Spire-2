"""Synthetic contracts, not gameplay or strength evidence."""
import unittest
import numpy as np
import torch
from rsi.ppo import ActorCritic
from rsi.phase_rl import STATE_SIZE,ACTION_SIZE
from rsi.task_value import Critic,Progress,task_features,balanced_weights,metrics,ridge_fit


class TaskValueTests(unittest.TestCase):
    def test_episode_balancing_and_metrics(self):
        ids=np.array([0,0,0,1]);w=balanced_weights(ids)
        self.assertAlmostEqual(float(w[:3].sum()),float(w[3]),places=6)
        m=metrics([0,0,0,1],[-1,-1,-1,1],ids)
        self.assertAlmostEqual(m['mse'],.5)
        self.assertIsNone(metrics([0,1],[1,1],[0,1])['ev'])

    def test_critic_isolated_and_matched_zero_extension(self):
        actor=ActorCritic(state_dim=STATE_SIZE,action_dim=ACTION_SIZE)
        old={k:v.clone() for k,v in actor.state_dict().items()};critic=Critic(actor)
        x=torch.randn(3,STATE_SIZE);z=torch.cat([x,torch.zeros(3,5)],1)
        torch.testing.assert_close(actor.state(x),critic.state(z))
        critic(z).sum().backward()
        self.assertTrue(all(p.grad is None for p in actor.parameters()))
        with torch.no_grad():critic.state[0].weight.add_(1)
        self.assertTrue(all(torch.equal(old[k],v) for k,v in actor.state_dict().items()))

    def test_progress_does_not_count_intermediate_card_selection(self):
        p=Progress(5);a=p.observe({'decision':'combat_play'})
        self.assertEqual(a['completed'],0)
        a=p.observe({'decision':'card_select'})
        self.assertEqual(a['completed'],0)
        self.assertEqual(p.observe({'decision':'card_reward','from_event':True})['completed'],0)
        a=p.observe({'decision':'card_reward','gold_earned':10,'player':{'hp':20}})
        self.assertEqual(a['completed'],1)
        self.assertEqual(p.observe({'decision':'potion_reward'})['completed'],1)
        np.testing.assert_allclose(task_features(a),[1,.6,1/6,5/6,.5])

    def test_ridge_constant_uses_episode_weights(self):
        coef=ridge_fit(np.ones((4,1)),np.array([-1,-1,-1,1.]),np.array([0,0,0,1]))
        self.assertAlmostEqual(float(coef[0]),0.,places=6)


if __name__=='__main__':unittest.main()
