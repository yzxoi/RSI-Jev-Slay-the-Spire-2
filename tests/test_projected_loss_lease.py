import copy
import json
from pathlib import Path
import unittest

from rsi.campaign import hard_endturn_review
from rsi.danger import review_projected_loss
from rsi.review_lease import ReviewLease, projected_loss_requires_expert


FIXTURE = json.loads((Path(__file__).parents[1] / 'experiments/E070/frozen-potion-lease.json').read_text())


class ProjectedLossLeaseTests(unittest.TestCase):
    def lease(self):
        state = copy.deepcopy(FIXTURE['after'])
        lease = ReviewLease.accepted_opener(FIXTURE['before'], state,
                                            FIXTURE['before_hash'], FIXTURE['after_hash'])
        self.assertIsNotNone(lease)
        self.assertTrue(lease.validate(state, FIXTURE['after_hash']))
        return lease, state

    def test_frozen_potion_opener_avoids_one_duplicate_pause(self):
        lease, state = self.lease()
        self.assertEqual(state['combat']['player']['cards_played_this_turn'], 0)
        projection = review_projected_loss(state, 20)
        self.assertEqual(projection, FIXTURE['baseline_projection'])
        self.assertTrue(projected_loss_requires_expert(projection, None))
        self.assertFalse(projected_loss_requires_expert(projection, lease))
        self.assertEqual(lease.suppressed_pauses, 1)

    def test_revoked_or_stale_lease_still_requires_review(self):
        for change, reason in [('new_turn', 'scope_changed'),
                               ('stale_hash', 'unexpected_state_change'),
                               ('unknown_attack', 'unmodelled_attack')]:
            with self.subTest(change=change):
                lease, state = self.lease()
                observed = FIXTURE['after_hash']
                if change == 'new_turn':
                    state['turn'] += 1
                elif change == 'stale_hash':
                    observed = 'changed-state'
                else:
                    state['combat']['enemies'][0]['intents'][0]['total_damage'] = None
                self.assertFalse(lease.validate(state, observed))
                self.assertEqual(lease.revoked_reason, reason)
                self.assertTrue(projected_loss_requires_expert(FIXTURE['baseline_projection'], lease))
                self.assertEqual(lease.suppressed_pauses, 0)

    def test_hard_lethal_end_turn_is_independent(self):
        lease, state = self.lease()
        state['combat']['end_turn_will_kill_player'] = True
        self.assertFalse(projected_loss_requires_expert(FIXTURE['baseline_projection'], lease))
        self.assertEqual(hard_endturn_review(state)[0], 'lethal_end_turn')


if __name__ == '__main__':
    unittest.main()
