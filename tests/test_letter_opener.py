import copy
import unittest

from rsi.planner import choose_plan


def fixture(starting_skills=2, relic=True, enemy_block=0):
    state = {
        'energy': 1,
        'skills_played_this_turn': starting_skills,
        'player': {'hp': 40, 'block': 0, 'relics': ([{'name': 'Letter Opener',
                                                    'vars': {'Cards': 3, 'Damage': 5}}] if relic else [])},
        'hand': [{'index': 0, 'id': 'CARD.DEFEND_IRONCLAD', 'type': 'Skill',
                  'cost': 1, 'stats': {'block': 5}, 'damage_by_target': []}],
        'enemies': [{'index': 0, 'hp': 3, 'block': enemy_block, 'intents': [{'total_damage': 0}]},
                    {'index': 1, 'hp': 26, 'block': 0, 'intents': [{'total_damage': 0}]}],
    }
    choices = [{'id': 'a000', 'action': {'action': 'play_card', 'args': {'card_index': 0}}},
               {'id': 'a001', 'action': {'action': 'end_turn', 'args': {}}}]
    return state, choices


class LetterOpenerTests(unittest.TestCase):
    def test_observed_third_skill_unblocked_transition(self):
        state, choices = fixture()
        _, plan = choose_plan(state, choices, letter_opener=True)
        self.assertEqual(plan['predicted_enemy_hp'], {0: 0, 1: 21})
        self.assertEqual(plan['predicted_block'], 5)
        self.assertEqual(plan['letter_opener_forecast']['procs'], 1)

    def test_sixth_skill_and_multiple_enemies(self):
        state, choices = fixture(starting_skills=5)
        _, plan = choose_plan(state, choices, letter_opener=True)
        self.assertEqual(plan['predicted_enemy_hp'], {0: 0, 1: 21})
        self.assertEqual(plan['letter_opener_forecast']['skills_after_plan'], 6)

    def test_fewer_skills_unknown_counter_and_absent_relic(self):
        for starting, relic in ((0, True), (None, True), (2, False)):
            with self.subTest(starting=starting, relic=relic):
                state, choices = fixture(starting_skills=starting, relic=relic)
                _, plan = choose_plan(state, choices, letter_opener=True)
                self.assertEqual(plan['predicted_enemy_hp'], {0: 3, 1: 26})
                if starting is None or not relic:
                    self.assertIsNone(plan['letter_opener_forecast'])

    def test_blocked_target_synthetic_ordering(self):
        state, choices = fixture(enemy_block=3)
        state['enemies'][0]['hp'] = 10
        _, plan = choose_plan(state, choices, letter_opener=True)
        self.assertEqual(plan['predicted_enemy_hp'], {0: 8, 1: 21})

    def test_absent_relic_does_not_change_baseline_choice(self):
        state, choices = fixture(relic=False)
        baseline = choose_plan(copy.deepcopy(state), choices)[0]
        treatment = choose_plan(copy.deepcopy(state), choices, letter_opener=True)[0]
        self.assertEqual(baseline['action'], treatment['action'])


if __name__ == '__main__':
    unittest.main()
