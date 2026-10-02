"""Synthetic math/optimizer checks, never battle-win evidence."""
import unittest
import numpy as np
import torch

from rsi.ppo import (ActorCritic, STATE_DIM, ACTION_DIM, MAX_ACTIONS, HP,
                     advantages, clipped_policy_loss, encode, padded, update)
from rsi.ppo_env import reward_for


class PPOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_gae_terminal_returns_and_truncation_bootstrap(self):
        adv, ret = advantages([0., 0., 1.], [.2, .3, .4], lam=1.)
        np.testing.assert_allclose(ret, [1., 1., 1.])
        np.testing.assert_allclose(adv, [.8, .7, .6], atol=1e-7)
        _, ret = advantages([0.], [.2], terminated=False, bootstrap=.8)
        self.assertAlmostEqual(float(ret[0]), .8)
        _, ret = advantages([-1.], [.8], bootstrap=100.)
        self.assertAlmostEqual(float(ret[0]), -1., places=6)

    def test_clip_handles_positive_and_negative_advantage(self):
        lp = torch.log(torch.tensor([1.5, .5]))
        loss = clipped_policy_loss(lp, torch.zeros(2), torch.tensor([1., -1.]))
        self.assertAlmostEqual(loss.item(), -.2, places=6)

    def test_mask_and_candidate_permutation(self):
        torch.manual_seed(1); model = ActorCritic()
        s = np.ones(STATE_DIM, np.float32); a = np.eye(ACTION_DIM, dtype=np.float32)[:3]
        dist, value = model(*padded([(s, a), (s, a[:1])]))
        self.assertEqual(dist.probs[1, 1:].sum().item(), 0.)
        permuted, v = model(*padded([(s, a[[2, 0, 1]])]))
        torch.testing.assert_close(permuted.probs[0], dist.probs[0, [2, 0, 1]])
        torch.testing.assert_close(v[0], value[0])

    def test_no_seed_leakage_and_overflow(self):
        state = {'decision': 'combat_play', 'player': {'hp': 20, 'max_hp': 80}, 'hand': [], 'enemies': []}
        choices = [{'name': 'End turn', 'action': {'action': 'end_turn', 'args': {}}}]
        a = encode(state, choices)
        b = encode({**state, 'seed': 'secret', 'run_id': 'different', 'context': {'seed': 'other'}}, choices)
        for x, y in zip(a, b): np.testing.assert_array_equal(x, y)
        with self.assertRaisesRegex(ValueError, 'overflowing'):
            encode(state, choices * (MAX_ACTIONS + 1))
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            encode({'decision': 'card_select', 'cards': [{}, {}, {}], 'min_select': 1, 'max_select': 2}, choices)

    def test_censored_outcomes_cannot_be_rewards(self):
        for status in ('timeout', 'action_cap', 'error'):
            with self.assertRaises(ValueError): reward_for({'status': status})
        self.assertGreater(reward_for({'status': 'clear', 'hp': 1, 'max_hp': 80}), 1)

    def test_optimizer_learns_synthetic_one_step_bandit(self):
        torch.manual_seed(23); rng = np.random.default_rng(23)
        model = ActorCritic(); optimizer = torch.optim.Adam(model.parameters(), lr=HP['lr'], eps=1e-5)
        s = np.zeros(STATE_DIM, np.float32)
        a = np.zeros((2, ACTION_DIM), np.float32); a[0, 0] = 1.; a[1, 0] = -1.
        observations = [(s, a)] * 128
        for _ in range(64):
            with torch.no_grad():
                dist, values = model(*padded(observations))
                indexes = dist.sample(); lps = dist.log_prob(indexes)
            episodes = [([dict(encoded=(s, a), index=int(i), logprob=float(lp), value=float(v))],
                         1. if int(i) == 0 else -1.) for i, lp, v in zip(indexes, lps, values)]
            metrics = update(model, optimizer, episodes, rng)
            self.assertTrue(np.isfinite(metrics['loss']))
        with torch.no_grad(): dist, _ = model(*padded([(s, a)]))
        self.assertGreater(dist.probs[0, 0].item(), .9)


if __name__ == '__main__':
    unittest.main()
