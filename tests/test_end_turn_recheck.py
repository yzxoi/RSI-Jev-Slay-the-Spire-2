import copy
import json
import unittest

from rsi.engine import ROOT, action
from rsi.end_turn_recheck import act1_clear, recheck_gate, review_payload
from rsi.policy import combat_candidates


class RecheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c['id']: c['state'] for c in json.loads((ROOT / 'experiments/E103/inputs.json').read_text())['cases']}

    def test_proposed_end_and_available_defense_are_both_required(self):
        state = self.cases['silent-dynamic-r07']
        choices = combat_candidates(state)
        end = choices[-1]
        self.assertTrue(recheck_gate(state, end, choices)['eligible'])
        self.assertFalse(recheck_gate(state, choices[0], choices)['eligible'])
        self.assertFalse(recheck_gate(state, end, [end])['eligible'])
        self.assertFalse(recheck_gate({**state, 'energy': 0}, end, choices)['eligible'])

    def test_covered_control_not_triggered_and_payload_does_not_mutate_state(self):
        covered = self.cases['silent-dynamic-r04']
        choices = combat_candidates(covered)
        self.assertFalse(recheck_gate(covered, choices[-1], choices)['eligible'])
        state = self.cases['silent-dynamic-r05']
        choices = combat_candidates(state)
        payload = {'state': copy.deepcopy(state), 'strategy': 'same'}
        old = copy.deepcopy(payload)
        revised = review_payload(payload, choices[-1], recheck_gate(state, choices[-1], choices))
        self.assertEqual(payload, old)
        self.assertEqual(revised['state'], old['state'])
        self.assertIn('end_turn', revised['end_turn_review']['limitations'])

    def test_potion_selection_and_preboss_rewards_are_not_act1_clears(self):
        reward = {'decision': 'card_reward', 'gold_earned': 20, 'player': {'hp': 10}}
        self.assertFalse(act1_clear(reward, False))
        self.assertTrue(act1_clear(reward, True))
        self.assertFalse(act1_clear({**reward, 'from_event': True}, True))
        self.assertFalse(act1_clear({'decision': 'card_reward', 'player': {'hp': 10}}, True))
        self.assertFalse(act1_clear({'decision': 'card_select', 'player': {'hp': 10}}, True))
        self.assertFalse(act1_clear({**reward, 'player': {'hp': 0}}, True))


if __name__ == '__main__':
    unittest.main()
