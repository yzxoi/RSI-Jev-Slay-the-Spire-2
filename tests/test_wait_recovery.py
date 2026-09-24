import copy
import unittest

from rsi.wait_recovery import read_after_accepted_action, GAME_THREAD_WAIT_ERROR


def state(turn, *, ready=True, run_id='run-1', screen='COMBAT'):
    return {'run_id': run_id, 'screen': screen, 'turn': turn,
            'run': {'floor': 11}, 'available_actions': ['play_card'] if ready else [],
            'combat': {'action_readiness': {'can_use_combat_actions': ready,
                                            'snapshot_stable': ready},
                       'player': {'energy': 3}, 'hand': [{'index': 0}]}}


class FakeMCP:
    def __init__(self, states, error=GAME_THREAD_WAIT_ERROR):
        self.states = list(states)
        self.error = error
        self.calls = []

    def call(self, name, arguments=None):
        self.calls.append(name)
        if name == 'wait_until_actionable':
            raise RuntimeError(self.error)
        if name == 'get_raw_game_state':
            return self.states.pop(0)
        raise AssertionError(f'Unexpected call: {name}')


class FakeTrace:
    def __init__(self):
        self.rows = []

    def write(self, kind, data):
        self.rows.append((kind, data))


class WaitRecoveryTests(unittest.TestCase):
    def clock(self):
        now = [0.]
        return lambda: now[0], lambda duration: now.__setitem__(0, now[0] + duration)

    def test_completed_action_wait_timeout_recovers_fresh_turn_without_act(self):
        before = state(2)
        mcp = FakeMCP([state(3, ready=False), state(3)])
        trace = FakeTrace()
        clock, sleep = self.clock()
        after = read_after_accepted_action(mcp, before, 'run-1', trace,
                                           clock=clock, sleep=sleep)
        self.assertEqual(after['turn'], 3)
        self.assertEqual(mcp.calls, ['wait_until_actionable',
                                      'get_raw_game_state', 'get_raw_game_state'])
        self.assertEqual([row[1]['status'] for row in trace.rows], ['started', 'recovered'])

    def test_changed_run_and_pause_stop(self):
        for snapshot in (state(3, run_id='other'), state(3, screen='PAUSE_MENU')):
            with self.subTest(snapshot=snapshot['screen'], run_id=snapshot['run_id']):
                mcp = FakeMCP([snapshot]); trace = FakeTrace()
                clock, sleep = self.clock()
                with self.assertRaises(RuntimeError):
                    read_after_accepted_action(mcp, state(2), 'run-1', trace,
                                               clock=clock, sleep=sleep)
                self.assertEqual(mcp.calls, ['wait_until_actionable', 'get_raw_game_state'])

    def test_unchanged_state_times_out_without_action(self):
        mcp = FakeMCP([copy.deepcopy(state(2)) for _ in range(3)])
        trace = FakeTrace(); clock, sleep = self.clock()
        with self.assertRaises(TimeoutError):
            read_after_accepted_action(mcp, state(2), 'run-1', trace,
                                       timeout=1., interval=.5, clock=clock, sleep=sleep)
        self.assertEqual(trace.rows[-1][1]['status'], 'timeout')
        self.assertNotIn('act', mcp.calls)

    def test_other_wait_error_is_not_masked(self):
        mcp = FakeMCP([], error='unexpected failure')
        with self.assertRaisesRegex(RuntimeError, 'unexpected failure'):
            read_after_accepted_action(mcp, state(2), 'run-1', FakeTrace())
        self.assertEqual(mcp.calls, ['wait_until_actionable'])


if __name__ == '__main__':
    unittest.main()
