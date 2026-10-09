import copy
import unittest

from rsi.coop_turn import wait_for_local_action


def state(*, ready=False, run_id='run', screen='COMBAT'):
    players = [{'player_id': str(i), 'is_local': i == 2,
                'is_connected': True, 'is_alive': True} for i in range(4)]
    return {'run_id': run_id, 'session': {'mode': 'multiplayer', 'phase': 'run',
                                        'control_scope': 'local_player'},
            'multiplayer': {'is_multiplayer': True, 'local_player_id': '2',
                            'player_count': 4},
            'screen': screen, 'turn': 2,
            'run': {'floor': 13, 'players': copy.deepcopy(players)},
            'combat': {'players': copy.deepcopy(players), 'action_readiness': {
                'can_use_combat_actions': ready, 'snapshot_stable': ready,
                'reason': 'ready' if ready else 'snapshot_stabilizing'}},
            'available_actions': ['play_card', 'end_turn'] if ready else ['discard_potion']}


class Fake:
    def __init__(self, next_states):
        self.states = iter(next_states)
        self.now = 0.
        self.calls = []
        self.events = []
        self.last = None

    def call(self, name):
        self.calls.append(name)
        self.last = next(self.states, self.last)
        return copy.deepcopy(self.last)

    def write(self, kind, data):
        self.events.append((kind, data))

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def run(self, first, *, deadline=20.):
        return wait_for_local_action(self, first, self, expected_run_id='run',
                                     local_player_id='2', player_count=4,
                                     deadline=deadline, clock=self.clock,
                                     sleep=self.sleep)


class CoopTurnTests(unittest.TestCase):
    def test_more_than_eight_seconds_of_unready_peer_activity_then_local_ready(self):
        changing = [state() for _ in range(20)]
        for i, raw in enumerate(changing):
            raw['combat']['peer_probe'] = i
        f = Fake(changing + [state(ready=True)])
        fresh, outcome = f.run(state())
        self.assertEqual(outcome, 'local_ready')
        self.assertTrue(fresh['combat']['action_readiness']['snapshot_stable'])
        self.assertGreater(f.now, 8.)
        self.assertEqual(set(f.calls), {'get_raw_game_state'})
        self.assertEqual(f.events[-1][1]['outcome'], 'local_ready')

    def test_snapshot_stable_without_local_permission_remains_unready(self):
        partial = state()
        partial['combat']['action_readiness']['snapshot_stable'] = True
        f = Fake([state(ready=True)])
        self.assertEqual(f.run(partial)[1], 'local_ready')
        self.assertEqual(len(f.calls), 1)

    def test_local_permission_without_stable_snapshot_remains_unready(self):
        partial = state()
        partial['combat']['action_readiness']['can_use_combat_actions'] = True
        f = Fake([state(ready=True)])
        self.assertEqual(f.run(partial)[1], 'local_ready')
        self.assertEqual(len(f.calls), 1)

    def test_run_or_local_owner_change_aborts_before_action(self):
        changed_owner = state()
        changed_owner['multiplayer']['local_player_id'] = '1'
        for changed in (state(run_id='other'), changed_owner):
            with self.subTest(changed=changed):
                f = Fake([changed])
                with self.assertRaises(RuntimeError):
                    f.run(state())
                self.assertEqual(set(f.calls), {'get_raw_game_state'})

    def test_scene_change_returns_without_waiting_for_combat_readiness(self):
        f = Fake([state(screen='MODAL')])
        fresh, outcome = f.run(state())
        self.assertEqual((fresh['screen'], outcome), ('MODAL', 'scene_changed'))

    def test_overall_deadline_stops_read_only_wait(self):
        f = Fake([state()])
        _, outcome = f.run(state(), deadline=3.)
        self.assertEqual(outcome, 'budget_boundary')
        self.assertGreaterEqual(f.now, 3.)
        self.assertEqual(set(f.calls), {'get_raw_game_state'})


if __name__ == '__main__':
    unittest.main()
