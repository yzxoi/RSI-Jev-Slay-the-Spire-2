import json
import unittest

from rsi.end_turn_check import arithmetic
from rsi.engine import ROOT


class NullablePowerInputsTest(unittest.TestCase):
    def test_recorded_null_power_states_match_empty_lists(self):
        cases = json.loads((ROOT / 'experiments/E105/inputs.json').read_text())['cases']
        for case in cases:
            with self.subTest(run_id=case['source_run_id']):
                state = case['state']
                self.assertIsNone(state['player_powers'])
                actual = arithmetic(state, plating=True)
                expected = arithmetic({**state, 'player_powers': []}, plating=True)
                actual.pop('seconds')
                expected.pop('seconds')
                self.assertEqual(actual, expected)
                self.assertEqual(actual['plating_block'], 0)


if __name__ == '__main__':
    unittest.main()
