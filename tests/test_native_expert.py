import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from rsi.native_expert import NativeExpert
from rsi.scenes import fingerprint


class NativeExpertTests(unittest.TestCase):
    def test_character_and_difficulty_are_part_of_native_freshness(self):
        base = dict(screen='CHARACTER_SELECT', run_id='run_unknown', character_select=dict(selected_character_id='IRONCLAD', ascension=0))
        for selection in (dict(selected_character_id='IRONCLAD', ascension=1), dict(selected_character_id='REGENT', ascension=0)):
            self.assertNotEqual(fingerprint(base), fingerprint({**base, 'character_select': selection}))

    def test_fresh_packet_binds_plan_and_rejects_stale_or_illegal_action(self):
        raw = dict(screen='MAP', run_id='test', run=dict(floor=1))
        action = dict(action='choose_map_node', option_index=2)
        good = dict(state_hash=fingerprint(raw), action=action, reason='test', campaign_plan='Preserve Boss potion')
        for change in ({}, {'state_hash': 'stale'}, {'action': dict(action='end_turn')}):
            with tempfile.TemporaryDirectory() as d:
                class FakeTrace:
                    directory = Path(d)
                    def write(self, *args): pass
                teacher = NativeExpert(Path(d)/'packets', FakeTrace(), time.monotonic()+10)
                with patch('rsi.native_expert.committed_response', return_value=({**good, **change}, 'test-commit')):
                    if change:
                        with self.assertRaises(ValueError): teacher.choose(raw, [dict(action=action)])
                    else:
                        self.assertEqual(teacher.choose(raw, [dict(action=action)]), good)
                        self.assertEqual(teacher.plan, good['campaign_plan'])
                        self.assertFalse((Path(d)/'pending-expert.json').exists())

    def test_stop_file_interrupts_wait_without_game_actions(self):
        with tempfile.TemporaryDirectory() as d:
            class FakeTrace:
                directory = Path(d)
                def write(self, *args): pass
            stop = Path(d)/'stop'; stop.touch()
            teacher = NativeExpert(Path(d)/'packets', FakeTrace(), time.monotonic()+10, stop)
            with self.assertRaisesRegex(RuntimeError, 'User requested stop'):
                teacher.choose(dict(screen='MAP', run_id='test', run=dict(floor=1)), [])
