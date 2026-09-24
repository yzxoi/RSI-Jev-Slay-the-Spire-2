import unittest

from rsi.boss_plan import plan_active, validate_boss_plan
from rsi.trace import digest


class BossPlanTests(unittest.TestCase):
    def test_exact_entry_and_room_expiry(self):
        state = {'decision': 'combat_play', 'context': {'act': 1, 'floor': 17,
                 'room_type': 'Boss', 'boss': {'id': 'BOSS.X'}},
                 'player': {'hp': 30}}
        plan = {'case_id': 'fixture', 'entry_state_hash': digest(state),
                'act': 1, 'floor': 17, 'boss_id': 'BOSS.X',
                'max_potions': 1, 'guidance': 'Use the available resource in this room.'}
        self.assertEqual(validate_boss_plan(plan, state), plan)
        self.assertTrue(plan_active(plan, state))
        self.assertFalse(plan_active(plan, {**state, 'decision': 'card_reward'}))
        self.assertFalse(plan_active(plan, {**state, 'context': {**state['context'], 'floor': 18}}))
        with self.assertRaises(ValueError):
            validate_boss_plan(plan, {**state, 'player': {'hp': 29}})
        with self.assertRaises(ValueError):
            validate_boss_plan({**plan, 'max_potions': 4}, state)


if __name__ == '__main__':
    unittest.main()
