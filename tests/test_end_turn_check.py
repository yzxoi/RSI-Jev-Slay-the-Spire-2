import copy
import json
import unittest

from rsi.engine import ROOT
from rsi.end_turn_check import arithmetic, boundary, branch_plans, fresh_discard


class EndTurnCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c['id']: c for c in json.loads((ROOT / 'experiments/E103/inputs.json').read_text())['cases']}

    def test_covered_control_is_not_missed_defense_with_plating(self):
        state = self.cases['silent-dynamic-r04']['state']
        self.assertEqual(arithmetic(state)['predicted_loss'], 1)
        result = arithmetic(state, True)
        self.assertEqual(result['predicted_loss'], 0)
        self.assertFalse(result['flags_missed_defense'])

    def test_nominations_preserve_discards_duplicates_and_report_cap(self):
        state = self.cases['silent-dynamic-r05']['state']
        result = branch_plans(state)
        self.assertEqual([p['discard_ordinal'] for p in result['plans'][1:]], [0, 1, 2])
        self.assertEqual(branch_plans(state, limit=1)['truncated'], 2)
        self.assertEqual(branch_plans(self.cases['silent-dynamic-r04']['state'])['alternative_count'], 3)

    def test_fresh_selection_uses_observed_indices_and_rejects_changed_shape(self):
        plan = {'discard_ordinal': 1, 'expected_discard_count': 2}
        state = {'decision': 'card_select', 'min_select': 1, 'max_select': 1,
                 'cards': [{'index': 4}, {'index': 9}]}
        self.assertEqual(fresh_discard(state, plan)['args']['indices'], '9')
        with self.assertRaises(ValueError):
            fresh_discard({**state, 'cards': [{'index': 4}]}, plan)
        with self.assertRaises(ValueError):
            fresh_discard({**state, 'min_select': 0}, plan)

    def test_nonterminal_selection_and_room_changes_are_not_next_turn(self):
        entry = self.cases['silent-dynamic-r05']['state']
        with self.assertRaises(ValueError):
            boundary(entry, entry)
        with self.assertRaises(ValueError):
            boundary({'decision': 'card_select'}, entry)
        after = copy.deepcopy(entry)
        after['round'] += 1
        self.assertEqual(boundary(after, entry), 'next_player_turn')
        after['context']['floor'] += 1
        with self.assertRaises(ValueError):
            boundary(after, entry)

    def test_unplayable_and_unsupported_cards_are_not_nominated(self):
        state = copy.deepcopy(self.cases['silent-dynamic-r05']['state'])
        next(c for c in state['hand'] if c['id'] == 'CARD.SURVIVOR')['can_play'] = False
        self.assertEqual(branch_plans(state)['alternative_count'], 0)


if __name__ == '__main__':
    unittest.main()
