import unittest

from rsi.potion_horizon import choose_horizon_potion


class PotionHorizonTests(unittest.TestCase):
    def state(self, room='Monster', floor=7, hp=20, potions=None):
        return {'decision': 'combat_play', 'context': {'act': 1, 'floor': floor, 'room_type': room},
                'round': 1, 'player': {'hp': hp, 'max_hp': 70, 'potions': potions or []},
                'enemies': [{'index': 4, 'hp': 18, 'block': 0,
                             'intents': [{'damage': 24}]}]}

    def test_boss_consumes_battle_long_buff_but_normal_fight_reserves_it(self):
        potion = {'index': 2, 'name': 'Dexterity Potion', 'target_type': 'AnyPlayer'}
        state = self.state(potions=[potion])
        choice, reason = choose_horizon_potion(state, {'predicted_total_hp_loss': 5})
        self.assertIsNone(choice)
        self.assertEqual(reason, 'reserve_for_future')
        state['context']['room_type'] = 'Boss'
        choice, reason = choose_horizon_potion(state, {'predicted_total_hp_loss': 5})
        self.assertEqual(choice['action']['args'], {'potion_index': 2})
        self.assertEqual(reason, 'boss_long_buff')
        state['context']['act'] = 2
        self.assertIsNone(choose_horizon_potion(state, {'predicted_total_hp_loss': 20})[0])

    def test_projected_lethal_uses_healing_before_damage(self):
        state = self.state(potions=[
            {'index': 0, 'name': 'Fire Potion', 'target_type': 'AnyEnemy', 'vars': {'Damage': 20}},
            {'index': 1, 'name': 'Blood Potion', 'target_type': 'AnyPlayer', 'vars': {'HealPercent': 20}}])
        choice, reason = choose_horizon_potion(state, {'predicted_total_hp_loss': 22})
        self.assertEqual(choice['action']['args'], {'potion_index': 1})
        self.assertEqual(reason, 'projected_lethal_rescue')

    def test_direct_damage_targets_attacker_only_when_it_kills(self):
        state = self.state(potions=[{'index': 0, 'name': 'Fire Potion',
                                     'target_type': 'AnyEnemy', 'vars': {'Damage': 20}}])
        choice, reason = choose_horizon_potion(state, {'predicted_total_hp_loss': 22})
        self.assertEqual(choice['action']['args'], {'potion_index': 0, 'target_index': 4})
        self.assertEqual(reason, 'projected_lethal_kill')
        state['enemies'][0]['hp'] = 30
        self.assertIsNone(choose_horizon_potion(state, {'predicted_total_hp_loss': 22})[0])
