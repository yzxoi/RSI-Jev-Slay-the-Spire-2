"""Synthetic boundary tests; no edited game states are win-rate evidence."""
import unittest
from rsi.curriculum import FightBoundary


class CurriculumBoundaryTests(unittest.TestCase):
    def test_initial_reward_is_not_success(self):
        b = FightBoundary()
        self.assertIsNone(b.observe(dict(decision='card_reward', gold_earned=10, player={'hp': 30})))
        self.assertIsNone(b.observe(dict(decision='map_select', player={'hp': 30})))
        self.assertFalse(b.started)

    def test_interrupted_reward_is_not_success(self):
        b = FightBoundary()
        b.observe(dict(decision='combat_play', context={'room_type': 'Elite', 'act': 1}))
        self.assertIsNone(b.observe(dict(decision='card_reward', from_event=True, player={'hp': 30})))
        self.assertIsNone(b.observe(dict(decision='card_select')))
        self.assertEqual(b.observe(dict(decision='card_reward', gold_earned=10, player={'hp': 30})), 'clear')
        self.assertEqual(b.room_type, 'Elite')

    def test_true_victory_death_and_boss(self):
        b = FightBoundary()
        b.observe(dict(decision='combat_play', context={'room_type': 'Boss', 'act': 3}))
        self.assertEqual(b.observe(dict(decision='game_over', victory=True)), 'clear')
        self.assertEqual(b.room_type, 'Boss')
        self.assertEqual(FightBoundary().observe(dict(decision='game_over', victory=False)), 'defeat')


if __name__ == '__main__':
    unittest.main()
