"""Synthetic statistical/choice checks, never win-rate evidence."""
import unittest
import numpy as np
from rsi.root_teacher import inverse_cdf, select_mean, utility


def result(status, hp=0):
    return dict(status=status, hp=hp, max_hp=80)


class RootTeacherTests(unittest.TestCase):
    def test_mean_rejects_lucky_maximum(self):
        actor = [result('clear', 10)]*4
        lucky = [result('clear', 80)]+[result('defeat')]*3
        self.assertEqual(select_mean([actor, lucky]), 0)

    def test_actor_tie_and_error(self):
        self.assertEqual(select_mean([[result('defeat')], [result('defeat')]]), 0)
        with self.assertRaises(ValueError):
            select_mean([[result('clear')], [result('timeout')]])

    def test_paired_uniform_supports_different_menus(self):
        self.assertEqual(inverse_cdf(np.array([.2, .8]), .2), 1)
        self.assertEqual(inverse_cdf(np.array([.0, .2, .8]), .0), 1)
        self.assertEqual(inverse_cdf(np.array([.5, .5]), .2), 0)
        with self.assertRaises(ValueError):
            inverse_cdf(np.array([.2, .2]), .2)

    def test_uncleared_initial_reward_has_no_value(self):
        with self.assertRaises(ValueError):
            utility(result('card_reward'))
        self.assertEqual(utility(result('defeat')), -1)


if __name__ == '__main__':
    unittest.main()
