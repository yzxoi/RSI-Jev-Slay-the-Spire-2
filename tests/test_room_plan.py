import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rsi.room_plan import load_room_plan, RoomPlanSession, room_complete, room_context
from rsi.scenes import candidates, fingerprint


class RoomPlanTest(unittest.TestCase):
    def setUp(self):
        self.raw = {'run_id': 'R1', 'screen': 'COMBAT', 'turn': 1,
                    'run': {'floor': 12, 'current_hp': 7,
                            'potions': [{'index': 1, 'potion_id': 'STRENGTH_POTION',
                                         'name': 'Strength', 'can_use': True,
                                         'requires_target': False}]},
                    'combat': {'hand': []}, 'available_actions': ['use_potion', 'end_turn']}
        self.plan = {'schema_version': 1, 'run_id': 'R1', 'floor': 12,
                     'start_state_hash': fingerprint(self.raw),
                     'opening_action': {'action': 'use_potion', 'option_index': 1},
                     'guidance': 'Spend the opening potion, then preserve 7 HP.'}

    def load(self, plan=None, raw=None):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            path.write_text(json.dumps(plan or self.plan))
            return load_room_plan(path, raw or self.raw)

    def test_room_plan_rejects_stale_state_or_illegal_opener(self):
        self.assertEqual(self.load(), self.plan)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.load(raw={**self.raw, 'run': {**self.raw['run'], 'current_hp': 6}})
        with self.assertRaisesRegex(ValueError, 'not currently legal'):
            self.load(plan={**self.plan, 'opening_action': {'action': 'use_potion', 'option_index': 0}})

    def test_opener_is_bound_and_accepted_once(self):
        session = RoomPlanSession(self.plan)
        self.assertEqual(session.opening(self.raw, candidates(self.raw))['action'], self.plan['opening_action'])
        with self.assertRaisesRegex(ValueError, 'state changed'):
            session.opening({**self.raw, 'turn': 2}, candidates(self.raw))
        session.accepted()
        with self.assertRaisesRegex(ValueError, 'already accepted'):
            session.opening(self.raw, candidates(self.raw))
        with self.assertRaisesRegex(ValueError, 'already accepted'):
            session.accepted()

    def test_room_guidance_expires_at_map(self):
        self.assertIn('room_plan', room_context(self.plan, self.raw))
        self.assertFalse(room_complete(self.plan, self.raw, 1))
        self.assertTrue(room_complete(self.plan, {'screen': 'MAP', 'run': {'floor': 12}}, 1))
        self.assertFalse(room_complete(self.plan, {'screen': 'MAP', 'run': {'floor': 12}}, 0))
        self.assertEqual(room_context(self.plan, {'screen': 'COMBAT', 'run': {'floor': 13}}), {})


if __name__ == '__main__':
    unittest.main()
