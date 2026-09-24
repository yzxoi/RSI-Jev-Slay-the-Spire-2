import unittest

from rsi.resource_check import resource_check


class ResourceCheckTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            'decision': 'combat_play', 'round': 2,
            'context': {'act': 1, 'floor': 7, 'room_type': 'Elite',
                        'boss': {'name': 'Known Boss'}},
            'player': {'hp': 55, 'max_hp': 80,
                       'potions': [{'index': 0, 'name': 'Block Potion', 'target_type': 'Self'},
                                   {'index': 1, 'name': 'Fire Potion', 'target_type': 'AnyEnemy'}]},
            'enemies': [{'index': 0, 'hp': 50, 'intents': [{'type': 'Attack', 'damage': 12}]}],
        }

    def test_spend_waits_for_actual_threat_and_uses_legal_targets(self):
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 7}))
        brief, choices = resource_check(self.state, {'predicted_total_hp_loss': 8})
        self.assertEqual(brief['reason'], 'stocked_material_threat')
        self.assertEqual([c['action']['action'] for c in choices], ['use_potion', 'use_potion'])
        self.assertEqual(choices[1]['action']['args']['target_index'], 0)
        self.state['enemies'][0]['intents'] = []
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 8}))

    def test_last_potion_requires_low_hp(self):
        self.state['player']['potions'] = self.state['player']['potions'][:1]
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 10}))
        self.state['player']['hp'] = 25
        brief, _ = resource_check(self.state, {'predicted_total_hp_loss': 5})
        self.assertEqual(brief['reason'], 'low_hp_material_threat')
        self.state['context']['act'] = 2
        self.assertIsNone(resource_check(self.state, {'predicted_total_hp_loss': 10}))


if __name__ == '__main__':
    unittest.main()
