import itertools
import unittest

from rsi.minimal_decision import (ARMS, answer_key, generate, request, rollout,
                                solve, verify_bank, make_bank)


class MinimalDecisionTests(unittest.TestCase):
    def test_solver_against_exhaustive_action_sequences(self):
        for h in (4, 8):
            item = generate('independent_solver_test', h, 'B', True)
            for field in ('world', 'flip_world', 'sham_world'):
                world = item[field]
                actual = {a: max(rollout(world, [a, *suffix])[1]
                    for suffix in itertools.product(('A', 'B'), repeat=h-1))
                    for a in ('A', 'B')}
                self.assertEqual(solve(world)[1][world['start']], actual)

    def test_midpoint_substitution_preserves_both_root_values(self):
        item = generate('midpoint_test', 16, 'A', False)
        world = item['world']
        full = solve(world)[1][world['start']]
        shortened = solve(world, item['boundary'])[1][world['start']]
        self.assertEqual(full, shortened)
        self.assertEqual(item['boundary']['layer'], 8)

    def test_remote_flip_and_sham_change_only_terminal_values(self):
        item = generate('counterfactual_test', 8, 'A', False)
        self.assertEqual(answer_key(item, 'choice'), 'A')
        self.assertEqual(answer_key(item, 'flip'), 'B')
        self.assertEqual(answer_key(item, 'sham'), 'A')
        for arm in ('flip', 'sham'):
            self.assertEqual(item['world']['edges'], item[arm+'_world']['edges'])
            self.assertEqual(sum(item['world']['payoffs'][s] != item[arm+'_world']['payoffs'][s]
                for s in item['world']['payoffs']), 2)

    def test_root_renaming_changes_label_without_changing_world_difficulty(self):
        one = generate('permutation_test', 8, 'A', True)
        two = generate('permutation_test', 8, 'B', True)
        self.assertEqual(one['attempts'], two['attempts'])
        self.assertEqual(one['world']['payoffs'], two['world']['payoffs'])
        q1, q2 = one['certificate']['root_q'], two['certificate']['root_q']
        self.assertEqual(q1, {'A': q2['B'], 'B': q2['A']})

    def test_requests_do_not_leak_reference_answers(self):
        item = generate('prompt_test', 4, 'B', False)
        for arm in ARMS:
            body = request(item, arm)
            self.assertEqual(set(body), {'model', 'state', 'questions'})
            self.assertNotIn('certificate', body['state'])
            self.assertNotIn('seed', body['state'])
            self.assertNotIn('prediction_answer', body['state'])
            if arm not in ('assisted', 'readout'):
                self.assertNotIn('verified_midpoint_values', body['state'])
                self.assertNotIn('exact_maximum_final_payoff_after_first_action', body['state'])

    def test_frozen_bank_is_complete_balanced_and_independently_verified(self):
        bank = make_bank()
        report = verify_bank(bank)
        self.assertTrue(report['passed'])
        self.assertEqual(report['items'], 36)
        self.assertEqual(report['cells'], 216)
        broken = make_bank()
        broken['items'][0]['certificate']['root_q']['A'] = -999
        with self.assertRaises(AssertionError):
            verify_bank(broken)


if __name__ == '__main__':
    unittest.main()
