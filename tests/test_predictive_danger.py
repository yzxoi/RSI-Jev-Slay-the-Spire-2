import copy
import gzip
import json
from pathlib import Path
import unittest

from rsi.danger import review_projected_loss


FIXTURE = json.loads(gzip.decompress((Path(__file__).parents[1] / 'experiments/E056/frozen-turn-starts.json.gz').read_bytes()))


def state(run_id, floor, turn):
    return copy.deepcopy(next(c['state'] for c in FIXTURE['cases'] if c['state']['run_id'] == run_id
                              and c['state']['run']['floor'] == floor and c['state']['turn'] == turn))


class PredictiveDangerTests(unittest.TestCase):
    def test_two_observed_e051_threshold_crossings_flag_before_cards(self):
        for floor, turn, hp, incoming in [(23, 6, 21, 28), (27, 4, 21, 16)]:
            with self.subTest(floor=floor):
                raw = state('F1GR9R0YXCCC', floor, turn)
                report = review_projected_loss(raw)
                self.assertTrue(report['review'])
                self.assertEqual((report['hp'], report['energy'], report['incoming']), (hp, 3, incoming))

    def test_no_attack_or_known_self_loss_does_not_alert(self):
        raw = state('F1GR9R0YXCCC', 27, 4)
        for enemy in raw['combat']['enemies']:
            enemy['intents'] = []
        self.assertFalse(review_projected_loss(raw)['review'])

    def test_multi_hit_and_two_attackers_are_summed(self):
        raw = state('F1GR9R0YXCCC', 23, 6)
        self.assertEqual(review_projected_loss(raw)['incoming'], 28)
        raw['combat']['enemies'][0]['intents'][0]['total_damage'] = 0
        self.assertEqual(review_projected_loss(raw)['incoming'], 20)

    def test_possible_immediate_kill_abstains(self):
        raw = state('F1GR9R0YXCCC', 27, 4)
        raw['combat']['enemies'][1]['current_hp'] = 30
        self.assertEqual(review_projected_loss(raw)['reason'], 'possible_immediate_attacker_kill')

    def test_unsettled_midturn_and_unknown_attack_abstain(self):
        raw = state('F1GR9R0YXCCC', 23, 6)
        raw['combat']['action_readiness']['snapshot_stable'] = False
        self.assertEqual(review_projected_loss(raw)['reason'], 'unsettled_or_stale')
        raw = state('F1GR9R0YXCCC', 23, 6)
        raw['combat']['player']['cards_played_this_turn'] = 1
        self.assertEqual(review_projected_loss(raw)['reason'], 'outside_turn_start')
        raw = state('F1GR9R0YXCCC', 23, 6)
        raw['combat']['enemies'][0]['intents'][0]['total_damage'] = None
        self.assertEqual(review_projected_loss(raw)['reason'], 'unknown_attack_total')

    def test_structured_beckon_loss_is_counted(self):
        raw = state('DCEND0WRAPGL', 17, 10)
        report = review_projected_loss(raw)
        self.assertEqual(report['known_self_loss'], 12)
        self.assertTrue(report['review'])
        beckon = next(c for c in raw['combat']['hand'] if c['card_id'] == 'BECKON')
        beckon['dynamic_values'] = []
        self.assertEqual(review_projected_loss(raw)['reason'], 'unknown_beckon_loss')

    def test_small_predicted_loss_does_not_add_review(self):
        raw = state('F1GR9R0YXCCC', 27, 4)
        raw['combat']['enemies'][1]['intents'][0]['total_damage'] = 13
        self.assertFalse(review_projected_loss(raw)['review'])
        raw['combat']['enemies'][1]['intents'][0]['total_damage'] = 14
        self.assertTrue(review_projected_loss(raw)['review'])


if __name__ == '__main__':
    unittest.main()
