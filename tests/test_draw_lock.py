import copy
import json
from pathlib import Path
import unittest

from rsi.planner import choose_plan


FIXTURE = json.loads((Path(__file__).parents[1] / 'experiments/E043/frozen-turn8.json').read_text())


class DrawLockTests(unittest.TestCase):
    def plan(self, state=None, candidates=None):
        return choose_plan(state or copy.deepcopy(FIXTURE['normalized_state']),
                           candidates or copy.deepcopy(FIXTURE['candidates']),
                           triggers=True, retaliation=True)

    def test_native_boss_hand_draws_with_pommel_before_battle_trance(self):
        chosen, plan = self.plan()
        self.assertEqual(chosen['card_id'], 'POMMEL_STRIKE')
        self.assertEqual(plan['plan_ids'][:2], ['a003', 'a002'])
        self.assertFalse(plan['initial_draw_locked'])
        self.assertTrue(plan['predicted_draw_locked'])

    def test_preexisting_native_and_headless_no_draw_remove_draw_benefit(self):
        for shape in ('native', 'headless'):
            with self.subTest(shape=shape):
                state = copy.deepcopy(FIXTURE['normalized_state'])
                if shape == 'native':
                    state['player']['powers'] = [{'power_id': 'NO_DRAW_POWER', 'name': '不可抽牌', 'amount': 1}]
                else:
                    state['player_powers'] = [{'name': 'No Draw', 'amount': 1}]
                chosen, plan = self.plan(state)
                self.assertEqual(chosen['card_id'], 'PERFECTED_STRIKE')
                self.assertTrue(plan['initial_draw_locked'])

    def test_no_battle_trance_control_keeps_attack_choice(self):
        state = copy.deepcopy(FIXTURE['normalized_state'])
        choices = copy.deepcopy(FIXTURE['candidates'])
        state['hand'] = [c for c in state['hand'] if c['id'] != 'BATTLE_TRANCE']
        choices = [c for c in choices if c['action'].get('card_index') != 2]
        chosen, plan = self.plan(state, choices)
        self.assertEqual(chosen['card_id'], 'PERFECTED_STRIKE')
        self.assertFalse(plan['predicted_draw_locked'])


if __name__ == '__main__':
    unittest.main()
