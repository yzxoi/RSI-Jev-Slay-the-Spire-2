import unittest

from rsi.event_guard import bound_bridge_reroll


def choices(suffix):
    return [
        {'action': {'action': 'choose_event_option', 'option_index': 0},
         'details': {'text_key': 'SLIPPERY_BRIDGE.pages.INITIAL.options.OVERCOME'}},
        {'action': {'action': 'choose_event_option', 'option_index': 1},
         'details': {'text_key': f'SLIPPERY_BRIDGE.pages.INITIAL.options.HOLD_ON_{suffix}'}},
    ]


class EventGuardTests(unittest.TestCase):
    def test_preserves_first_reroll_on_high_hp_offer(self):
        offered = choices('0')
        kept, report = bound_bridge_reroll(
            {'screen': 'EVENT', 'event': {'event_id': 'SLIPPERY_BRIDGE'},
             'run': {'current_hp': 86}}, offered)
        self.assertEqual(kept, offered)
        self.assertFalse(report['excluded'])

    def test_excludes_escalating_reroll_but_keeps_exit(self):
        offered = choices('1')
        kept, report = bound_bridge_reroll(
            {'screen': 'EVENT', 'event': {'event_id': 'SLIPPERY_BRIDGE'},
             'run': {'current_hp': 83}}, offered)
        self.assertEqual(kept, offered[:1])
        self.assertTrue(report['excluded'])

    def test_excludes_loop_stage_without_localized_cost_parsing(self):
        offered = choices('LOOP')
        kept, report = bound_bridge_reroll(
            {'screen': 'EVENT', 'event': {'event_id': 'SLIPPERY_BRIDGE'}}, offered)
        self.assertEqual(kept, offered[:1])
        self.assertTrue(report['excluded'])

    def test_other_events_remain_unchanged(self):
        offered = choices('1')
        kept, report = bound_bridge_reroll(
            {'screen': 'EVENT', 'event': {'event_id': 'OTHER'}}, offered)
        self.assertEqual(kept, offered)
        self.assertIsNone(report)

    def test_never_removes_only_action(self):
        offered = choices('1')[1:]
        kept, report = bound_bridge_reroll(
            {'screen': 'EVENT', 'event': {'event_id': 'SLIPPERY_BRIDGE'}}, offered)
        self.assertEqual(kept, offered)
        self.assertFalse(report['excluded'])
