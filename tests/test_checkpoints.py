import json
from pathlib import Path
import tempfile
import unittest

from rsi.checkpoints import differences, require_map, wire_pairs


class CheckpointTests(unittest.TestCase):
    def test_never_accept_a_combat_room_as_a_map_checkpoint(self):
        require_map({'decision': 'map_select', 'context': {'room_type': 'Map'}})
        for state in ({'decision': 'map_select', 'context': {'room_type': 'Elite'}},
                      {'decision': 'combat_play', 'context': {'room_type': 'Map'}}):
            with self.assertRaises(ValueError):
                require_map(state)

    def test_differences_preserve_relevant_field_paths_and_missing_null(self):
        a = {'player': {'hp': 10, 'deck': [{'id': 'a'}]}, 'x': None}
        b = {'player': {'hp': 9, 'deck': [{'id': 'b'}]}}
        self.assertEqual({x['path'] for x in differences(a, b)},
                         {'/player/hp', '/player/deck/0/id', '/x'})

    def test_wire_rejects_uncertain_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'wire.jsonl'
            p.write_text(json.dumps({'kind': 'command', 'data': {'cmd': 'start_run'}}) + '\n')
            with self.assertRaises(ValueError):
                wire_pairs(p)


if __name__ == '__main__':
    unittest.main()
