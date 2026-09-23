import copy
import gzip
import json
from pathlib import Path
import unittest

from rsi.campaign import hard_endturn_review
from rsi.danger import review_projected_loss
from rsi.review_lease import ReviewLease, current_hp_review


FIXTURE = json.loads((Path(__file__).parents[1] / 'experiments/E061/frozen-floor8-review.json').read_text())
RECORDS = FIXTURE['records']


class ReviewLeaseTests(unittest.TestCase):
    def opener(self):
        row = RECORDS[0]
        lease = ReviewLease.accepted_opener(row['before'], row['after'],
                                            row['before_hash'], row['after_hash'])
        self.assertIsNotNone(lease)
        return lease, copy.deepcopy(row['after'])

    def test_frozen_floor8_reduces_seven_approvals_to_two(self):
        approvals = 0; suppressed = 0
        for turn in (3, 4):
            rows = [r for r in RECORDS if r['before']['turn'] == turn]
            first = rows[0]; approvals += 1
            lease = ReviewLease.accepted_opener(first['before'], first['after'],
                                                first['before_hash'], first['after_hash'])
            self.assertIsNotNone(lease)
            for row in rows[1:]:
                self.assertEqual(lease.expected_hash, row['before_hash'])
                self.assertTrue(current_hp_review(row['before'], 20))
                self.assertTrue(lease.validate(row['before'], row['before_hash']))
                self.assertTrue(lease.suppress_current_hp_pause())
                lease.accepted_transition(row['after'], row['after_hash'])
            suppressed += lease.suppressed_pauses
        self.assertEqual((approvals, suppressed), (2, 5))

    def test_changed_run_new_turn_and_stale_fingerprint_revoke(self):
        for change, expected in [('run', 'scope_changed'), ('turn', 'scope_changed'),
                                 ('hash', 'unexpected_state_change')]:
            with self.subTest(change=change):
                lease, state = self.opener()
                observed = lease.expected_hash
                if change == 'run': state['run_id'] = 'OTHER'
                if change == 'turn': state['turn'] += 1
                if change == 'hash': observed = 'unexpected'
                self.assertFalse(lease.validate(state, observed))
                self.assertEqual(lease.revoked_reason, expected)
                self.assertFalse(lease.suppress_current_hp_pause())

    def test_unknown_attack_or_unsafe_beckon_revokes(self):
        lease, state = self.opener()
        attack = next(i for e in state['combat']['enemies'] if e['is_alive']
                      for i in e['intents'] if i['intent_type'] == 'Attack')
        attack['total_damage'] = None
        lease.expected_hash = 'synthetic-unknown-attack'
        self.assertFalse(lease.validate(state, lease.expected_hash))
        self.assertEqual(lease.revoked_reason, 'unmodelled_attack')

        lease, state = self.opener()
        state['combat']['hand'].append({'index': 99, 'card_id': 'BECKON',
                                        'dynamic_values': [{'name': 'HpLoss', 'current_value': 30}]})
        lease.expected_hash = 'synthetic-lethal-beckon'
        self.assertFalse(lease.validate(state, lease.expected_hash))
        self.assertEqual(lease.revoked_reason, 'unsafe_beckon_loss')
        self.assertEqual(hard_endturn_review(state)[0], 'projected_lethal_beckon_end_turn')

    def test_newly_lethal_end_turn_remains_hard_guarded(self):
        lease, state = self.opener()
        state['combat']['end_turn_will_kill_player'] = True
        lease.expected_hash = 'synthetic-lethal-end'
        self.assertTrue(lease.validate(state, lease.expected_hash))
        self.assertEqual(hard_endturn_review(state)[0], 'lethal_end_turn')

    def test_projected_large_loss_review_is_independent_of_lease(self):
        data = json.loads(gzip.decompress((Path(__file__).parents[1]
                                          / 'experiments/E056/frozen-turn-starts.json.gz').read_bytes()))
        state = next(x['state'] for x in data['cases'] if x['state']['run_id'] == 'F1GR9R0YXCCC'
                     and x['state']['run']['floor'] == 23 and x['state']['turn'] == 6)
        self.assertFalse(current_hp_review(state, 20))  # Current HP is 21.
        self.assertTrue(review_projected_loss(state, 20)['review'])

    def test_lease_only_after_same_turn_combat_opener(self):
        row = RECORDS[0]
        after = copy.deepcopy(row['after']); after['turn'] += 1
        self.assertIsNone(ReviewLease.accepted_opener(row['before'], after,
                                                     row['before_hash'], 'after'))
        before = copy.deepcopy(row['before']); before['screen'] = 'REWARD'
        self.assertIsNone(ReviewLease.accepted_opener(before, row['after'],
                                                     row['before_hash'], row['after_hash']))


if __name__ == '__main__':
    unittest.main()
