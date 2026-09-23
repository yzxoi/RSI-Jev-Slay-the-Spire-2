import copy
import json
from pathlib import Path
import unittest

from rsi.campaign import ordinary_candidates
from rsi.live_plan import plan_native


FIXTURE = json.loads((Path(__file__).parents[1] / 'experiments/E046/frozen-dominated-end.json').read_text())


class NativeEndTurnGuardTests(unittest.TestCase):
    def frozen(self):
        return copy.deepcopy(FIXTURE['raw']), copy.deepcopy(FIXTURE['candidates'])

    def test_guided_jev_cannot_end_with_three_useful_defends(self):
        raw, offered = self.frozen()
        choices, guard = ordinary_candidates(raw, offered, 'floor_guided')
        self.assertTrue(guard['excluded'])
        self.assertEqual(guard['incoming'], 14)
        self.assertEqual(len(guard['witness_ids']), 3)
        self.assertEqual({c['action']['action'] for c in choices}, {'play_card'})
        selected, plan = plan_native(raw, choices, triggers=True, retaliation=True)
        self.assertIn(selected, choices)
        self.assertEqual(selected['card_id'], 'DEFEND_IRONCLAD')
        self.assertEqual(plan['predicted_total_hp_loss'], 9)

    def test_explicit_choice_and_raw_jev_keep_all_legal_actions(self):
        raw, offered = self.frozen()
        for policy, explicit in [('floor_guided', True), ('room_guided', True), ('jev', False)]:
            with self.subTest(policy=policy, explicit=explicit):
                choices, guard = ordinary_candidates(raw, offered, policy, explicit_choice=explicit)
                self.assertEqual(choices, offered)
                self.assertIsNone(guard)

    def test_unknown_power_and_ice_cream_disable_conservative_filter(self):
        for control in ('unknown_power', 'ice_cream'):
            with self.subTest(control=control):
                raw, offered = self.frozen()
                if control == 'unknown_power':
                    raw['combat']['enemies'][0]['powers'].append({'power_id': 'UNMODELED_RETALIATION_POWER', 'amount': 1})
                else:
                    raw['run']['relics'].append({'relic_id': 'ICE_CREAM', 'name': 'Ice Cream'})
                choices, guard = ordinary_candidates(raw, offered, 'floor_guided')
                self.assertFalse(guard['excluded'])
                self.assertIn(offered[-1], choices)

    def test_no_incoming_or_no_playable_card_leaves_end_turn(self):
        raw, offered = self.frozen()
        raw['combat']['enemies'][0]['intents'] = []
        choices, guard = ordinary_candidates(raw, offered, 'floor_guided')
        self.assertFalse(guard['excluded'])
        self.assertIn(offered[-1], choices)
        raw, offered = self.frozen()
        for card in raw['combat']['hand']:
            card['playable'] = False
        choices, guard = ordinary_candidates(raw, offered[-1:], 'floor_guided')
        self.assertFalse(guard['excluded'])
        self.assertEqual(choices, offered[-1:])


if __name__ == '__main__':
    unittest.main()
