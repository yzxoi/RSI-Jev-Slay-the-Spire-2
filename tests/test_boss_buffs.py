import unittest

from rsi.boss_buffs import choose_boss_buff
from rsi.policy import combat_candidates


class BossBuffTests(unittest.TestCase):
    def state(self):
        return {'decision': 'combat_play', 'context': {'act': 1, 'room_type': 'Boss'},
                'round': 1, 'player': {'potions': [
                    {'index': 0, 'name': 'Attack Potion', 'target_type': 'AnyPlayer'},
                    {'index': 1, 'name': 'Dexterity Potion', 'target_type': 'AnyPlayer'},
                    {'index': 2, 'name': 'Liquid Bronze', 'target_type': 'AnyPlayer'}]},
                'enemies': [{'index': 5, 'hp': 30}], 'hand': []}

    def test_boss_opener_uses_legal_persistent_buffs_in_order(self):
        state = self.state()
        cards = combat_candidates(state)
        choice, expanded = choose_boss_buff(state, cards)
        self.assertEqual(choice['name'], 'Liquid Bronze')
        self.assertEqual(choice['action']['args'], {'potion_index': 2})
        self.assertIn(choice, expanded)
        state['player']['potions'].pop()
        choice, expanded = choose_boss_buff(state, cards)
        self.assertEqual(choice['name'], 'Dexterity Potion')
        state['player']['potions'].pop()
        choice, expanded = choose_boss_buff(state, cards)
        self.assertIsNone(choice)
        self.assertIs(expanded, cards)

    def test_outside_first_act_boss_opener_reserves_all_potions(self):
        state = self.state()
        cards = combat_candidates(state)
        for context, round_number in [({'act': 1, 'room_type': 'Elite'}, 1),
                                      ({'act': 2, 'room_type': 'Boss'}, 1),
                                      ({'act': 1, 'room_type': 'Boss'}, 2)]:
            state['context'], state['round'] = context, round_number
            choice, expanded = choose_boss_buff(state, cards)
            self.assertIsNone(choice)
            self.assertIs(expanded, cards)
