import unittest

from rsi.boss_plan import resolve_opening_action, validate_boss_plan
from rsi.trace import digest


class BossDirectiveTests(unittest.TestCase):
    def setUp(self):
        self.state = {'decision': 'combat_play',
                      'context': {'act': 1, 'floor': 17, 'room_type': 'Boss',
                                  'boss': {'id': 'BOSS.X'}},
                      'hand': [{'index': 2, 'id': 'CARD.AOE'},
                               {'index': 3, 'id': 'CARD.TARGET'}],
                      'enemies': [{'index': 0, 'name': 'Follower'},
                                  {'index': 1, 'name': 'Leader'}]}
        self.plan = {'case_id': 'fixture', 'entry_state_hash': digest(self.state),
                     'act': 1, 'floor': 17, 'boss_id': 'BOSS.X',
                     'max_potions': 1, 'guidance': 'Use the opener.',
                     'opening_actions': [{'kind': 'potion', 'potion_name': 'Duplicator'},
                                         {'kind': 'card', 'card_id': 'CARD.AOE'}]}
        self.choices = [
            {'name': 'Duplicator', 'action': {'action': 'use_potion', 'args': {'potion_index': 4}}},
            {'name': 'AoE', 'action': {'action': 'play_card', 'args': {'card_index': 2}}},
            {'name': 'Target', 'action': {'action': 'play_card', 'args': {'card_index': 3, 'target_index': 0}}},
            {'name': 'Target', 'action': {'action': 'play_card', 'args': {'card_index': 3, 'target_index': 1}}},
        ]

    def test_exact_entry_and_fresh_semantic_resolution(self):
        self.assertEqual(validate_boss_plan(self.plan, self.state, require_directives=True), self.plan)
        self.assertEqual(resolve_opening_action(self.plan['opening_actions'][0], self.state, self.choices), self.choices[0])
        self.assertEqual(resolve_opening_action(self.plan['opening_actions'][1], self.state, self.choices), self.choices[1])
        self.assertEqual(resolve_opening_action({'kind': 'card', 'card_id': 'CARD.TARGET',
                                                 'target_name': 'Leader'}, self.state, self.choices), self.choices[3])

    def test_rejects_stale_ambiguous_or_illegal_actions(self):
        with self.assertRaises(ValueError):
            validate_boss_plan(self.plan, {**self.state, 'hand': []}, require_directives=True)
        with self.assertRaises(ValueError):
            validate_boss_plan({**self.plan, 'opening_actions': []}, self.state, require_directives=True)
        with self.assertRaises(ValueError):
            resolve_opening_action({'kind': 'card', 'card_id': 'CARD.TARGET'}, self.state, self.choices)
        with self.assertRaises(ValueError):
            resolve_opening_action({'kind': 'potion', 'potion_name': 'Missing'}, self.state, self.choices)


if __name__ == '__main__':
    unittest.main()
