import copy
import json
from pathlib import Path
import unittest

from rsi.scenes import candidates
from rsi.selection_guard import preserve_exhaust_block


FIXTURE = Path(__file__).resolve().parents[1] / 'experiments/E064/frozen-selection.json'


def frozen():
    return copy.deepcopy(json.loads(FIXTURE.read_text())['raw'])


class SelectionGuardTests(unittest.TestCase):
    def test_frozen_native_exhaust_selection_preserves_evil_eye(self):
        raw = frozen()
        offered = candidates(raw)
        kept, report = preserve_exhaust_block(raw, offered)
        self.assertEqual(report, {'applied': True, 'reason': 'preserve_affordable_conditional_block',
                                  'incoming': 31, 'hp': 36, 'block': 0, 'energy': 2,
                                  'protected_option_indices': [3], 'protected_block': {3: 18}})
        self.assertEqual({c['action']['option_index'] for c in kept}, {0, 1, 2})
        self.assertLess(len(kept), len(offered))

    def test_does_not_filter_other_selection_or_safe_threat(self):
        for change in ('upgrade', 'no_attack', 'enough_block', 'unaffordable', 'invalid_cost'):
            with self.subTest(change=change):
                raw = frozen()
                if change == 'upgrade':
                    raw['selection']['prompt'] = '选择一张牌升级'
                elif change == 'no_attack':
                    for enemy in raw['combat']['enemies']:
                        enemy['intents'] = []
                elif change == 'enough_block':
                    raw['combat']['player']['block'] = 31
                elif change == 'unaffordable':
                    raw['combat']['player']['energy'] = 0
                else:
                    raw['selection']['cards'][3]['energy_cost'] = -1
                offered = candidates(raw)
                kept, report = preserve_exhaust_block(raw, offered)
                self.assertEqual(kept, offered)
                self.assertFalse(report['applied'])

    def test_never_removes_only_legal_target(self):
        raw = frozen()
        raw['selection']['cards'] = [raw['selection']['cards'][3]]
        offered = candidates(raw)
        kept, report = preserve_exhaust_block(raw, offered)
        self.assertEqual(kept, offered)
        self.assertFalse(report['applied'])
