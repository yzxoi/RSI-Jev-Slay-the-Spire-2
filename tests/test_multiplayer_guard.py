import copy
import unittest

from rsi.multiplayer_guard import require_local_multiplayer


class MultiplayerGuardTests(unittest.TestCase):
    def setUp(self):
        players = [
            {'player_id': str(i), 'is_local': i == 2, 'is_connected': True, 'is_alive': True}
            for i in range(4)
        ]
        self.raw = {
            'session': {'mode': 'multiplayer', 'phase': 'run', 'control_scope': 'local_player'},
            'multiplayer': {'is_multiplayer': True, 'local_player_id': '2', 'player_count': 4},
            'screen': 'COMBAT', 'run': {'players': copy.deepcopy(players)},
            'combat': {'players': copy.deepcopy(players)},
        }

    def test_valid_local_player(self):
        self.assertEqual(require_local_multiplayer(self.raw, expected_player_count=4), '2')

    def test_rejects_changed_actor_or_roster(self):
        for mutate in (
            lambda r: r['multiplayer'].update(local_player_id='1'),
            lambda r: r['run']['players'][2].update(is_local=False),
            lambda r: r['combat']['players'][1].update(is_local=True),
            lambda r: r['multiplayer'].update(player_count=3),
            lambda r: r['session'].update(control_scope='team'),
        ):
            with self.subTest(mutate=mutate):
                raw = copy.deepcopy(self.raw)
                mutate(raw)
                with self.assertRaises(RuntimeError):
                    require_local_multiplayer(raw, expected_player_count=4, expected_local_id='2')


if __name__ == '__main__':
    unittest.main()
