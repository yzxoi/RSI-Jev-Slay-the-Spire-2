import json
from pathlib import Path
import unittest

from rsi.live_plan import normalize
from rsi.planner import choose_plan, hard_to_kill_cap


OBSERVED = json.loads((Path(__file__).parents[1] / 'experiments/E062/frozen-native-hits.json').read_text())['records']


def observed_state(row):
    card_id = row['card_id']; hits = row['card_hits']; damage = row['card_preview_damage_per_hit']
    value_name = 'CalculatedDamage' if card_id == 'PERFECTED_STRIKE' else 'Damage'
    card = {'index': 0, 'card_id': card_id, 'name': card_id, 'energy_cost': 1,
            'target_type': 'AnyEnemy', 'requires_target': True, 'valid_target_indices': [0],
            'playable': True, 'dynamic_values': [{'name': value_name, 'base_value': damage,
                                                   'current_value': damage}]}
    if hits > 1:
        card['dynamic_values'].append({'name': 'Repeat', 'base_value': hits,
                                       'current_value': hits})
    return {'run': {'deck': [{'card_id': card_id, 'card_type': 'Attack'}], 'relics': []},
            'combat': {'player': {'energy': 1, 'current_hp': 40, 'block': 0,
                                  'powers': [], 'cards_played_this_turn': 0},
                       'enemies': [{'index': 0, 'current_hp': row['enemy_hp_before'],
                                    'block': 0, 'intents': [], 'powers': [row['enemy_power']] }],
                       'hand': [card]}}


def play(index=0):
    return {'id': f'a{index:03}', 'action': {'action': 'play_card', 'card_index': index,
                                          'target_index': 0}, 'name': 'attack'}


class HitCapTests(unittest.TestCase):
    def test_three_observed_native_hit_deltas(self):
        for row in OBSERVED:
            with self.subTest(card=row['card_id']):
                state = normalize(observed_state(row))
                self.assertEqual(hard_to_kill_cap(state['enemies'][0]), 9)
                _, plan = choose_plan(state, [play()], retaliation=True, hit_cap=True)
                self.assertEqual(plan['predicted_enemy_hp'][0], row['enemy_hp_after'])
                _, baseline = choose_plan(state, [play()], retaliation=True)
                if row['card_preview_damage_per_hit'] > 9:
                    self.assertLess(baseline['predicted_enemy_hp'][0], row['enemy_hp_after'])

    def test_synthetic_multi_hit_beats_capped_single_hit(self):
        state = {'energy': 2, 'player': {'hp': 20, 'block': 0},
                 'enemies': [{'index': 0, 'hp': 12, 'block': 0, 'intents': [{'total_damage': 10}],
                              'powers': [{'power_id': 'HARD_TO_KILL_POWER', 'amount': 9}]}],
                 'hand': [{'index': 0, 'id': 'HEAVY', 'cost': 2, 'type': 'Attack', 'stats': {},
                           'damage_by_target': [{'target_index': 0, 'native_base_damage': 24,
                                                 'native_hits': 1}]},
                          {'index': 1, 'id': 'TWO_HITS', 'cost': 2, 'type': 'Attack', 'stats': {},
                           'damage_by_target': [{'target_index': 0, 'native_base_damage': 6,
                                                 'native_hits': 2}]}]}
        choices = [play(0), play(1)]
        base, _ = choose_plan(state, choices, retaliation=True)
        treated, plan = choose_plan(state, choices, retaliation=True, hit_cap=True)
        self.assertEqual(base['action']['card_index'], 0)
        self.assertEqual(treated['action']['card_index'], 1)
        self.assertEqual(plan['predicted_enemy_hp'][0], 0)

    def test_synthetic_block_then_hp_cap_and_unrelated_control(self):
        state = {'energy': 1, 'player': {'hp': 20, 'block': 0},
                 'enemies': [{'index': 0, 'hp': 20, 'block': 5, 'intents': [],
                              'powers': [{'power_id': 'HARD_TO_KILL_POWER', 'amount': 9}]}],
                 'hand': [{'index': 0, 'id': 'SINGLE', 'cost': 1, 'type': 'Attack', 'stats': {},
                           'damage_by_target': [{'target_index': 0, 'native_base_damage': 15,
                                                 'native_hits': 1}]}]}
        _, capped = choose_plan(state, [play()], retaliation=True, hit_cap=True)
        self.assertEqual(capped['predicted_enemy_hp'][0], 11)
        state['enemies'][0]['powers'] = []
        _, control = choose_plan(state, [play()], retaliation=True, hit_cap=True)
        _, baseline = choose_plan(state, [play()], retaliation=True)
        self.assertEqual(control['predicted_enemy_hp'], baseline['predicted_enemy_hp'])


if __name__ == '__main__':
    unittest.main()
