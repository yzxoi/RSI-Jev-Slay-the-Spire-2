import unittest

from rsi.teacher import select, terminal


class TeacherSafetyTests(unittest.TestCase):
    def test_potion_reward_is_not_victory(self):
        self.assertIsNone(terminal({'decision': 'card_reward', 'from_event': True,
                                    'player': {'hp': 20}}))
        self.assertEqual(terminal({'decision': 'card_reward', 'gold_earned': 30,
                                   'player': {'hp': 20}}), 'boss_clear')
        with self.assertRaises(RuntimeError):
            terminal({'decision': 'card_reward', 'player': {'hp': 20}})

    def test_death_never_counts_as_clear(self):
        for state in ({'decision': 'game_over', 'player': {'hp': 0}},
                      {'decision': 'card_reward', 'gold_earned': 10, 'player': {'hp': 0}}):
            self.assertEqual(terminal(state), 'boss_defeat')

    def test_fresh_hand_and_target_indices(self):
        policy = dict(mode='focus_leader', loss_price=1.5, potions='none')
        state = dict(decision='combat_play', round=1, energy=1, player={'hp': 20},
                     enemies=[dict(index=7, hp=20, intents=[], powers=[])],
                     hand=[dict(index=4, id='CARD.STRIKE', name='Strike', can_play=True,
                                cost=1, type='Attack', target_type='AnyEnemy',
                                stats={'damage': 6}, damage_by_target=[{'target_index': 7, 'damage': 6}])])
        chosen, choices, _ = select(state, policy)
        self.assertEqual(chosen['action']['args'], {'card_index': 4, 'target_index': 7})
        state['hand'][0]['index'] = 0
        chosen, choices, _ = select(state, policy)
        self.assertEqual(chosen['action']['args'], {'card_index': 0, 'target_index': 7})
        self.assertIn(chosen, choices)

    def test_card_selection_after_potion_remains_legal(self):
        policy = dict(mode='balanced', loss_price=1.5, potions='early')
        state = dict(decision='card_reward', from_event=True, player={'hp': 30},
                     cards=[dict(index=2, id='CARD.POWER', name='Power', type='Power', stats={}),
                            dict(index=5, id='CARD.OTHER', name='Other', type='Power', stats={})])
        chosen, choices, _ = select(state, policy)
        self.assertEqual(chosen['action']['action'], 'select_card_reward')
        self.assertIn(chosen['action']['args']['card_index'], (2, 5))


if __name__ == '__main__':
    unittest.main()
