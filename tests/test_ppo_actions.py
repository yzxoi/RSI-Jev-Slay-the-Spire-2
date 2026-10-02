"""Synthetic exhaustive menu checks; not a game-strength benchmark."""
import itertools
import unittest
from unittest.mock import patch
import numpy as np
import torch

from rsi.full import macro_candidates
from rsi.ppo import ActorCritic, encode, padded
from rsi.ppo_actions import ACTION_LIMIT, complete_choices


def state(n, lo, hi):
    return dict(decision='card_select', min_select=lo, max_select=hi,
                cards=[dict(index=i * 2, name=f'Card {i}', id=f'CARD.X{i}') for i in range(n)])


class CompleteMenuTests(unittest.TestCase):
    def test_all_subsets_and_zero_choice_are_exact(self):
        for n, lo, hi in [(0, 0, 0), (5, 1, 1), (6, 0, 6), (19, 0, 2), (10, 0, 10)]:
            s = state(n, lo, hi)
            cs = complete_choices(s)
            actual = [tuple(int(x) for x in c['action']['args'].get('indices', '').split(',') if x) for c in cs]
            expected = [c for k in range(lo, min(hi, n) + 1)
                        for c in itertools.combinations([i * 2 for i in range(n)], k)]
            self.assertEqual(set(actual), set(expected))
            self.assertEqual(len(actual), len(set(actual)))

    def test_supported_legacy_menus_remain_byte_identical(self):
        for n, lo, hi in [(0, 0, 0), (10, 1, 1), (6, 0, 6), (15, 1, 2)]:
            s = state(n, lo, hi)
            old, new = macro_candidates(s, resource_decisions=True), complete_choices(s)
            self.assertEqual(old, new)
            for a, b in zip(encode(s, old), encode(s, new, max_actions=ACTION_LIMIT)):
                np.testing.assert_array_equal(a, b)

    def test_oversize_fails_before_enumeration(self):
        with patch('rsi.ppo_actions.macro_candidates') as enumerate_menu:
            with self.assertRaisesRegex(ValueError, 'resource bound'):
                complete_choices(state(20, 0, 20))
            enumerate_menu.assert_not_called()

    def test_large_menu_actor_padding_and_gradients(self):
        torch.set_num_threads(1)
        s = state(19, 0, 2); e = encode(s, complete_choices(s), max_actions=ACTION_LIMIT)
        m = ActorCritic()
        self.assertEqual(sum(p.numel() for p in m.parameters()), 73794)
        dist, value = m(*padded([e, (e[0], e[1][:1])]))
        self.assertEqual(dist.probs.shape, (2, 191))
        self.assertAlmostEqual(dist.probs[0].sum().item(), 1., places=5)
        self.assertEqual(dist.probs[1, 1:].sum().item(), 0.)
        (-dist.log_prob(torch.tensor([190, 0])).mean() + value.square().mean()).backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters()))


if __name__ == '__main__': unittest.main()
