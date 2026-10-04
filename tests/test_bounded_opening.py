"""Synthetic selection invariants; no game-strength claim."""
import copy
import unittest

from rsi.bounded_opening import bounded_choices
from rsi.opening_subset import candidate_id, indexes, opening_domain
from rsi.run_env import legal_choices


class BoundedOpeningTests(unittest.TestCase):
    def fixture(self):
        state = dict(decision='card_select', min_select=0, max_select=999999999,
            context=dict(act=1, floor=2, room_type='Monster'), player=dict(relics=[dict(name='Gambling Chip')]),
            cards=[dict(index=i, name=f'card-{i}', type='Status' if i == 2 else 'Attack') for i in range(5)])
        domain = opening_domain(state, dict(action='select_map_node'), dict(decision='map_select', context=dict(act=1, floor=1)))
        choices = legal_choices(state, {})
        baseline = next(c for c in choices if indexes(c) == [0, 1])
        return state, domain, choices, baseline

    def test_fixed_priors_dedup_and_order_independence(self):
        state, domain, choices, baseline = self.fixture()
        selected = bounded_choices(state, choices, baseline, domain)
        self.assertEqual(len(selected), 8)
        self.assertEqual(len({candidate_id(c) for c in selected}), 8)
        for required in ([0, 1], [], [0, 1, 2, 3, 4], [2]):
            self.assertIn(required, [indexes(c) for c in selected])
        self.assertEqual(selected, bounded_choices(state, list(reversed(choices)), baseline, domain))
        all_choice = next(c for c in choices if len(indexes(c)) == 5)
        self.assertEqual(len(bounded_choices(state, choices, all_choice, domain)), 8)

    def test_stale_or_incomplete_menus_rejected(self):
        state, domain, choices, baseline = self.fixture()
        changed = copy.deepcopy(state); changed['cards'][0]['type'] = 'Curse'
        with self.assertRaises(ValueError): bounded_choices(changed, choices, baseline, domain)
        with self.assertRaises(ValueError): bounded_choices(state, choices[:-1], baseline, domain)
        with self.assertRaises(ValueError): bounded_choices(state, choices[:-1] + [choices[0]], baseline, domain)
