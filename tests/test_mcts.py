"""Synthetic algorithm tests; never counted as game outcomes."""
import random
import unittest
from unittest.mock import patch

from rsi.mcts import Flat, Node, UCT
from rsi.battle_search import TreePolicy, boundary, rank, utility, search
from rsi.trace import digest


def actions(*names):
    return [{'action': {'cmd': 'action', 'action': n, 'args': {}}} for n in names]


class TreeTests(unittest.TestCase):
    def test_uct_explores_then_allocates_more_to_good_action(self):
        tree = UCT(random.Random(0))
        choices = actions('good', 'bad')
        for _ in range(100):
            c, child, _ = tree.choose(tree.root, 'root', choices)
            tree.backup([tree.root, child], float(c['action']['action'] == 'good'))
        counts = {c['action']['action']: tree.root.children[digest(c['action'])].visits for c in choices}
        self.assertGreater(counts['good'], 80)
        self.assertGreater(counts['bad'], 0)
        self.assertEqual(tree.root.visits, 100)

    def test_flat_balances_attempts_including_unscored_caps(self):
        tree = Flat(random.Random(1))
        selected = [tree.choose('root', actions('a', 'b', 'c'))[0]['action']['action'] for _ in range(31)]
        counts = [selected.count(c) for c in ('a', 'b', 'c')]
        self.assertLessEqual(max(counts) - min(counts), 1)
        self.assertEqual(tree.root.visits, 0)

    def test_nodes_validate_observations_without_state_transpositions(self):
        tree = UCT(random.Random(2))
        choices = actions('a', 'b')
        _, a, _ = tree.choose(tree.root, 'root', choices)
        a.bind('same')
        tree.backup([tree.root, a], 1)
        _, b, _ = tree.choose(tree.root, 'root', choices)
        b.bind('same')
        self.assertIsNot(a, b)
        self.assertEqual(b.visits, 0)
        with self.assertRaises(ValueError):
            a.bind('different')
        with self.assertRaises(ValueError):
            tree.choose(tree.root, 'root', actions('a'))

    def test_tree_can_expand_beyond_root_and_back_up_all_ancestors(self):
        tree = UCT(random.Random(0))
        for iteration in range(3):
            policy = TreePolicy(tree, random.Random(0))
            for depth in range(iteration + 1):
                _, source = policy.choose({'depth': depth}, actions('only'), None)
                self.assertEqual(source, 'tree')
                policy.observe({'depth': depth + 1})
            tree.backup(policy.path, 1.)
        self.assertEqual(tree.max_depth, 3)
        self.assertEqual(tree.root.visits, 3)

    def test_error_and_censored_results_cannot_be_scored(self):
        for status in ('error', 'timeout', 'action_cap'):
            with self.assertRaises(ValueError):
                rank({'status': status})
            with self.assertRaises(ValueError):
                utility({'status': status}, {})
        with self.assertRaises(ValueError):
            UCT(random.Random()).backup([Node()], 1.5)

    def test_clear_dominates_resource_rich_defeat_and_generated_reward_is_not_clear(self):
        self.assertGreater(rank(dict(status='clear', hp=1, potions=[], steps=100)),
                           rank(dict(status='defeat', hp=99, potions=['x'], steps=1)))
        self.assertIsNone(boundary({'decision': 'card_reward', 'from_event': True}))

    def test_budget_cap_preserves_certified_incumbent_and_verifies_it(self):
        plan = [{'before': 'a', 'action': {}, 'after': 'b'}]
        control = dict(status='clear', hp=5, potions=[], steps=1, seconds=150,
                       replay_seconds=1, path_hash='path', plan=plan, final_hash='b')
        with patch('rsi.battle_search.probe', return_value=control) as run:
            result = search({'case': 'synthetic'}, {}, 'uct', control)
        self.assertEqual(result['status'], 'time_cap')
        self.assertEqual(result['incumbent']['hp'], 5)
        self.assertEqual(result['simulations'], 1)
        self.assertEqual(run.call_args.kwargs['expected_plan'], plan)

    def test_divergent_final_replay_invalidates_result(self):
        control = dict(status='clear', hp=5, potions=[], steps=1, seconds=150,
                       replay_seconds=1, path_hash='path', plan=[], final_hash='a')
        divergent = {**control, 'final_hash': 'b'}
        with patch('rsi.battle_search.probe', return_value=divergent):
            result = search({'case': 'synthetic'}, {}, 'flat', control)
        self.assertEqual(result['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()
