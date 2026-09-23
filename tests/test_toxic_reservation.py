import copy
import json
from pathlib import Path
import unittest

from rsi.campaign import ordinary_candidates


FIXTURE = json.loads((Path(__file__).parents[1] / 'experiments/E047/frozen-mytes.json').read_text())


def frozen(name):
    case = next(c for c in FIXTURE['cases'] if c['name'] == name)
    return copy.deepcopy(case['state']), copy.deepcopy(case['candidates'])


class ToxicReservationTests(unittest.TestCase):
    def test_real_turn2_start_still_allows_attack_with_two_energy_left(self):
        state, offered = frozen('turn2_start')
        kept, report = ordinary_candidates(state, offered, 'floor_guided')
        self.assertEqual(len(kept), 12)
        self.assertEqual(report['toxic_reservation']['clear_needed'], 2)
        self.assertEqual(report['toxic_reservation']['excluded_ids'], ['a012'])
        self.assertIn('a008', [c['id'] for c in kept])  # Actual first Molten Fist remained legal.

    def test_real_after_molten_reserves_both_toxic_plays(self):
        state, offered = frozen('after_molten')
        kept, report = ordinary_candidates(state, offered, 'floor_guided')
        self.assertEqual([c['id'] for c in kept], ['a000', 'a001'])
        self.assertEqual(report['toxic_reservation']['current_projected_loss'], 14)
        self.assertEqual(report['toxic_reservation']['cleared_projected_loss'], 6)
        self.assertNotIn('a002', [c['id'] for c in kept])  # Actual losing Replay Strike.

    def test_synthetic_after_one_toxic_reserves_last_energy(self):
        state, offered = frozen('after_molten')
        state['combat']['player']['energy'] = 1
        state['combat']['hand'] = [c for c in state['combat']['hand'] if c['index'] != 0]
        offered = [c for c in offered if c['action'].get('card_index') != 0 or c['action']['action'] != 'play_card']
        kept, report = ordinary_candidates(state, offered, 'floor_guided')
        self.assertEqual([c['id'] for c in kept], ['a001'])
        self.assertEqual(report['toxic_reservation']['clear_needed'], 1)

    def test_high_hp_and_no_toxic_controls_do_not_filter_attacks(self):
        state, offered = frozen('after_molten')
        state['combat']['player']['current_hp'] = 80
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertEqual(kept, offered)
        state, offered = frozen('after_molten')
        state['combat']['hand'] = [c for c in state['combat']['hand'] if c['card_id'] != 'TOXIC']
        offered = [c for c in offered if c['action'].get('card_index') not in (0, 1) or c['action']['action'] != 'play_card']
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertEqual(kept, offered)

    def test_plausible_immediate_kill_and_unknown_effect_abstain(self):
        state, offered = frozen('after_molten')
        state['combat']['enemies'][0]['current_hp'] = 18
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertIn('a002', [c['id'] for c in kept])
        state, offered = frozen('after_molten')
        state['combat']['hand'][2]['card_id'] = 'UNKNOWN_ATTACK'
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertIn('a002', [c['id'] for c in kept])
        state, offered = frozen('after_molten')
        state['combat']['enemies'][0]['powers'] = [{'power_id': 'VULNERABLE_POWER', 'amount': 2}]
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertIn('a002', [c['id'] for c in kept])
        state, offered = frozen('after_molten')
        state['combat']['enemies'][0]['intents'] = [{'total_damage': 12}]
        state['combat']['enemies'][1]['intents'] = [{'total_damage': 1}]
        kept, _ = ordinary_candidates(state, offered, 'floor_guided')
        self.assertIn('a002', [c['id'] for c in kept])

    def test_raw_jev_and_explicit_choice_remain_unfiltered(self):
        state, offered = frozen('after_molten')
        for policy, explicit in [('jev', False), ('floor_guided', True)]:
            kept, report = ordinary_candidates(state, offered, policy, explicit_choice=explicit)
            self.assertEqual(kept, offered)
            self.assertIsNone(report)


if __name__ == '__main__':
    unittest.main()
