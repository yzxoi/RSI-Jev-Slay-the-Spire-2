import copy
import json
from pathlib import Path
import unittest

from rsi.planner import choose_plan
from rsi.full import advance_skill_counter
from rsi.policy import combat_candidates
from rsi.live_plan import plan_native


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

    def test_opaque_auto_play_makes_counter_unknown_until_new_turn(self):
        self.assertEqual(advance_skill_counter(2, {'id': 'CARD.DEFEND_IRONCLAD', 'type': 'Skill'}), 3)
        self.assertIsNone(advance_skill_counter(2, {'id': 'CARD.CASCADE', 'type': 'Skill'}))
        self.assertIsNone(advance_skill_counter(None, {'id': 'CARD.DEFEND_IRONCLAD', 'type': 'Skill'}))

    def test_frozen_regression_does_not_plan_through_purity_selection(self):
        path = Path(__file__).resolve().parents[1] / 'experiments/E063/frozen-divergence.json'
        state = json.loads(path.read_text())
        state['skills_played_this_turn'] = 0
        choices = combat_candidates(state)
        selected, plan = choose_plan(state, choices, letter_opener=True)
        self.assertNotEqual(selected.get('card_id'), 'CARD.PURITY')
        ids = plan['plan_ids']
        purity_ids = {c['id'] for c in choices if c.get('card_id') == 'CARD.PURITY'}
        self.assertFalse(any(candidate in purity_ids for candidate in ids[:-1]))

    def test_native_adapter_uses_observed_skill_count(self):
        raw = {'run': {'deck': [], 'relics': [{'relic_id': 'LETTER_OPENER'}]},
               'combat': {'player': {'current_hp': 40, 'energy': 1, 'block': 0,
                                     'skills_played_this_turn': 2, 'powers': []},
                          'enemies': [{'index': 0, 'current_hp': 3, 'block': 0, 'is_alive': True,
                                       'powers': [], 'intents': [{'total_damage': 0}]},
                                      {'index': 1, 'current_hp': 26, 'block': 0, 'is_alive': True,
                                       'powers': [], 'intents': [{'total_damage': 0}]}],
                          'hand': [{'index': 0, 'card_id': 'DEFEND_IRONCLAD', 'name': 'Defend',
                                    'requires_target': False, 'energy_cost': 1, 'playable': True,
                                    'target_type': None,
                                    'dynamic_values': [{'name': 'Block', 'base_value': 5,
                                                        'current_value': 5}]}]}}
        choices = [{'id': 'a000', 'action': {'action': 'play_card', 'card_index': 0}},
                   {'id': 'a001', 'action': {'action': 'end_turn'}}]
        _, plan = plan_native(raw, choices, letter_opener=True)
        self.assertEqual(plan['predicted_enemy_hp'], {0: 0, 1: 21})
        self.assertEqual(plan['letter_opener_forecast']['starting_skills'], 2)


if __name__ == '__main__':
    unittest.main()
