import copy
import gzip
import json
from pathlib import Path
import unittest

from rsi.campaign import ordinary_candidates
from rsi.status_guard import beckon_endturn_projection, reserve_beckon_energy


FIXTURE = json.loads(gzip.decompress((Path(__file__).parents[1] / 'experiments/E055/frozen-soul-fysh.json.gz').read_bytes()))


def case(index):
    row = FIXTURE['cases'][index]
    return copy.deepcopy(row['state']), copy.deepcopy(row['candidates'])


class BeckonReservationTests(unittest.TestCase):
    def test_native_final_energy_preserves_beckon_and_excludes_nonlethal_strikes(self):
        state, offered = case(55)
        kept, report = ordinary_candidates(state, offered, 'room_guided')
        self.assertEqual([c['id'] for c in kept], ['a001'])
        self.assertEqual(report['beckon_reservation']['current_projected_loss'], 16)
        self.assertEqual(report['beckon_reservation']['cleared_projected_loss'], 10)
        self.assertEqual(report['beckon_reservation']['excluded_ids'], ['a000', 'a002'])

    def test_native_energy_zero_exposes_native_false_negative(self):
        state, offered = case(56)
        self.assertFalse(state['combat']['end_turn_will_kill_player'])
        projection = beckon_endturn_projection(state)
        self.assertEqual((projection['hp'], projection['projected_loss']), (13, 16))
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)

    def test_nonlethal_and_no_beckon_controls(self):
        state, offered = case(55)
        state['combat']['player']['current_hp'] = 30
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)
        state, offered = case(55)
        state['combat']['hand'] = [h for h in state['combat']['hand'] if h['card_id'] != 'BECKON']
        self.assertIsNone(beckon_endturn_projection(state))
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)

    def test_multiple_beckons_require_both_energy_and_playability(self):
        state, offered = case(55)
        state['combat']['player']['current_hp'] = 13
        state['combat']['player']['energy'] = 2
        other = copy.deepcopy(next(h for h in state['combat']['hand'] if h['card_id'] == 'BECKON'))
        other['index'] = 4
        state['combat']['hand'].append(other)
        offered.insert(2, {'id': 'new_beckon', 'action': {'action': 'play_card', 'card_index': 4}})
        kept, report = reserve_beckon_energy(state, offered)
        self.assertEqual(report['clear_needed'], 2)
        self.assertEqual({c['id'] for c in kept}, {'a001', 'new_beckon'})
        state['combat']['player']['energy'] = 1
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)
        state['combat']['player']['energy'] = 2
        other['playable'] = False
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)

    def test_sufficient_block_and_lethal_attack_without_beckon(self):
        state, offered = case(55)
        state['combat']['player']['block'] = 25
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)
        state['combat']['hand'] = [h for h in state['combat']['hand'] if h['card_id'] != 'BECKON']
        state['combat']['player']['block'] = 0
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)

    def test_plausible_immediate_kill_and_unknown_hploss_abstain(self):
        state, offered = case(55)
        state['combat']['enemies'][0]['current_hp'] = 6
        kept, _ = reserve_beckon_energy(state, offered)
        self.assertIn('a000', [c['id'] for c in kept])
        state, offered = case(55)
        beckon = next(h for h in state['combat']['hand'] if h['card_id'] == 'BECKON')
        beckon['dynamic_values'] = []
        self.assertFalse(beckon_endturn_projection(state)['known'])
        self.assertEqual(reserve_beckon_energy(state, offered)[0], offered)

    def test_raw_jev_and_explicit_choice_do_not_change_candidates(self):
        state, offered = case(55)
        for policy, explicit in [('jev', False), ('room_guided', True)]:
            kept, report = ordinary_candidates(state, offered, policy, explicit_choice=explicit)
            self.assertEqual(kept, offered)
            self.assertIsNone(report)


if __name__ == '__main__':
    unittest.main()
