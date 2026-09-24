import unittest

from rsi.resource_check import resource_check


class ResourceCheckTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            'decision': 'combat_play', 'round': 1,
            'context': {'act': 1, 'floor': 7, 'room_type': 'Elite',
                        'boss': {'name': 'Known Boss'}},
            'player': {'hp': 48, 'max_hp': 80,
                       'potions': [{'index': 0, 'name': 'Block Potion',
                                    'target_type': 'Self'}]},
            'enemies': [{'index': 0, 'hp': 50, 'intents': [{'type': 'Attack', 'damage': 12}]}],
        }

    def test_elite_opener_has_reserve_and_legal_potion(self):
        brief, choices = resource_check(self.state, {'predicted_total_hp_loss': 8})
        self.assertEqual(brief['reason'], 'elite_or_boss_opener')
        self.assertEqual(brief['known_boss'], 'Known Boss')
        self.assertEqual([c['action']['action'] for c in choices],
                         ['reserve_potions', 'use_potion'])
        self.assertEqual(choices[1]['action']['args']['potion_index'], 0)

    def test_monster_check_requires_low_hp_and_predicted_loss(self):
        self.state['context']['room_type'] = 'Monster'
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 8}))
        self.state['player']['hp'] = 30
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 4}))
        brief, _ = resource_check(self.state, {'predicted_total_hp_loss': 5})
        self.assertEqual(brief['reason'], 'low_hp_attacking_monster')
        self.state['context']['act'] = 2
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 20}))


if __name__ == '__main__':
    unittest.main()
