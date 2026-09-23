import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rsi.floor_plan import load_floor_plan, plan_complete, plan_context
from rsi.scenes import fingerprint


class FloorPlanTest(unittest.TestCase):
    def setUp(self):
        self.raw = {'run_id': 'R1', 'screen': 'MAP', 'run': {'floor': 7}}
        self.plan = {'schema_version': 1, 'run_id': 'R1', 'start_floor': 7,
                     'target_floor': 8, 'start_state_hash': fingerprint(self.raw),
                     'guidance': 'Preserve HP until the next rest.'}

    def load(self, plan=None, raw=None):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            path.write_text(json.dumps(plan or self.plan))
            return load_floor_plan(path, raw or self.raw)

    def test_plan_binds_exact_start_state(self):
        self.assertEqual(self.load(), self.plan)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.load(raw={'run_id': 'R1', 'screen': 'MAP', 'run': {'floor': 7, 'current_hp': 1}})
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.load(raw={'run_id': 'OTHER', 'screen': 'MAP', 'run': {'floor': 7}})

    def test_one_floor_expiry_and_boundary(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.load(plan={**self.plan, 'target_floor': 9})
        room = {'run': {'floor': 8}, 'screen': 'COMBAT'}
        self.assertIn('floor_plan', plan_context(self.plan, room))
        self.assertFalse(plan_complete(self.plan, room, 4))
        self.assertTrue(plan_complete(self.plan, {'run': {'floor': 8}, 'screen': 'MAP'}, 4))
        self.assertFalse(plan_complete(self.plan, {'run': {'floor': 8}, 'screen': 'MAP'}, 0))
        self.assertEqual(plan_context(self.plan, {'run': {'floor': 9}, 'screen': 'COMBAT'}), {})


if __name__ == '__main__':
    unittest.main()
