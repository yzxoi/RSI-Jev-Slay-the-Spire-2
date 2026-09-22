import json
from pathlib import Path
import tempfile
import unittest
from rsi.jev import Budget
from rsi.policy import combat_candidates
from rsi.trace import Trace


class RuntimeTests(unittest.TestCase):
    def test_current_indices_and_unplayable_exclusion(self):
        state = {"hand": [{"index": 4, "id": "strike", "name": "Strike", "can_play": True, "target_type": "AnyEnemy"},
                           {"index": 9, "can_play": False}], "enemies": [{"index": 2}, {"index": 5}]}
        choices = combat_candidates(state)
        self.assertEqual([c["action"]["args"] for c in choices[:-1]],
                         [{"card_index": 4, "target_index": 2}, {"card_index": 4, "target_index": 5}])
        self.assertEqual(choices[-1]["action"]["action"], "end_turn")

    def test_request_budget_and_unknown_usage_stop(self):
        budget = Budget(1, 1)
        budget.acquire()
        budget.settle({"cost": .0001})
        with self.assertRaises(RuntimeError):
            budget.acquire()
        budget = Budget(2, 1)
        budget.acquire()
        budget.settle({})
        with self.assertRaises(RuntimeError):
            budget.acquire()

    def test_trace_preserves_failure_and_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Trace(directory, {"run_id": "test"})
            trace.write("failure", {"error": "timeout"})
            digest = trace.close()
            rows = [json.loads(l) for l in (Path(directory) / "decisions.jsonl").read_text().splitlines()]
            self.assertEqual([r["seq"] for r in rows], [0, 1])
            self.assertEqual(rows[-1]["data"]["error"], "timeout")
            self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
