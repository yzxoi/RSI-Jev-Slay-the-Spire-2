import unittest

from rsi.combat_brief import finish_combat, reward_brief, start_combat, update_combat


class CombatBriefTests(unittest.TestCase):
    def test_uses_actual_transition_and_same_floor_only(self):
        fight = {'decision': 'combat_play', 'context': {'act': 1, 'floor': 7, 'room_type': 'Elite'},
                 'round': 1, 'player': {'hp': 52, 'max_hp': 80},
                 'enemies': [{'name': 'Test Elite'}]}
        combat = start_combat(fight)
        update_combat(combat, {**fight, 'round': 6})
        reward = {'decision': 'card_reward', 'context': {'act': 1, 'floor': 7,
                  'boss': {'name': 'Test Boss'}}, 'player': {'hp': 30, 'max_hp': 80}}
        telemetry = finish_combat(combat, reward)
        brief = reward_brief(reward, telemetry)
        self.assertEqual((telemetry['rounds'], telemetry['net_hp_loss']), (6, 22))
        self.assertEqual(brief['known_boss'], 'Test Boss')
        self.assertEqual(brief['preceding_fight']['hp_in'], 52)
        self.assertIn('Survival is critical', brief['decision_guidance'])
        self.assertIsNone(reward_brief({**reward, 'context': {'act': 1, 'floor': 8}}, telemetry))
        self.assertIsNone(reward_brief({**reward, 'decision': 'map_select'}, telemetry))


if __name__ == '__main__':
    unittest.main()
