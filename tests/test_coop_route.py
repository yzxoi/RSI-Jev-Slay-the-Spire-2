import unittest

from rsi.coop_route import route_candidates, waiting_for_peer_route, wait_for_map_vote_ack


def state(*, vote=None, peer_votes=0, screen='MAP', floor=3, current=None):
    return {
        'run_id': 'example', 'screen': screen,
        'session': {'mode': 'multiplayer'}, 'run': {'floor': floor},
        'map': {'current_node': current or {'row': 2, 'col': 0}, 'local_vote': vote,
                'available_nodes': [{'index': 0, 'row': 3, 'col': 0,
                                     'vote_count': peer_votes,
                                     'has_local_vote': vote is not None}]},
    }


class FakeMcp:
    def __init__(self, states):
        self.states = iter(states)
        self.reads = 0

    def call(self, name):
        assert name == 'get_raw_game_state'
        self.reads += 1
        return next(self.states)


class FakeTrace:
    def __init__(self):
        self.rows = []

    def write(self, kind, data):
        self.rows.append((kind, data))


class CoopRouteTests(unittest.TestCase):
    def test_waits_for_peer_before_voting_and_after_local_vote(self):
        self.assertEqual(route_candidates(state()), [])
        self.assertTrue(waiting_for_peer_route(state()))
        self.assertEqual(len(route_candidates(state(peer_votes=1))), 1)
        self.assertEqual(route_candidates(state(vote={'row': 3, 'col': 0}, peer_votes=2)), [])

    def test_acknowledges_only_observed_vote_or_transition(self):
        before = state(peer_votes=1)
        for acknowledged in (state(vote={'row': 3, 'col': 0}, peer_votes=2),
                             state(peer_votes=0, screen='COMBAT', floor=4)):
            mcp = FakeMcp([before, acknowledged])
            trace = FakeTrace()
            self.assertIs(wait_for_map_vote_ack(mcp, before, {'option_index': 0}, trace,
                                                sleep=lambda _: None), acknowledged)
            self.assertEqual(mcp.reads, 2)
            self.assertEqual(trace.rows[-1][0], 'map_vote_ack')

    def test_unacknowledged_vote_stops_without_resend(self):
        before = state(peer_votes=1)
        mcp = FakeMcp([before, before])
        trace = FakeTrace()
        tick = iter([0., 0., 1., 1.])
        with self.assertRaisesRegex(RuntimeError, 'refusing to resend'):
            wait_for_map_vote_ack(mcp, before, {'option_index': 0}, trace,
                                  timeout=.5, clock=lambda: next(tick), sleep=lambda _: None)
        self.assertEqual(mcp.reads, 2)
        self.assertEqual(trace.rows[-1][1]['outcome'], 'unconfirmed')


if __name__ == '__main__':
    unittest.main()
