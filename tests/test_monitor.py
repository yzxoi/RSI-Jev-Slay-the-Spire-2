"""Decision monitor uses trace evidence without becoming a game writer."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from rsi.monitor import Projection, TraceFeed, serve


def row(seq, kind, data):
    return {"seq": seq, "time": 1000 + seq, "kind": kind, "data": data}


def append(path, *records, complete=True):
    with path.open("ab") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False).encode())
            if complete:
                file.write(b"\n")


class MonitorTests(unittest.TestCase):
    def test_partial_append_jev_mapping_and_no_invented_confidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "segment" / "decisions.jsonl"
            path.parent.mkdir()
            append(path, row(0, "manifest", {"scope": "native_complete_run", "config": {"expected_run_id": "RUN"}}),
                   row(1, "before", {"state": {"run_id": "RUN", "screen": "COMBAT", "run": {"floor": 5, "current_hp": 12, "max_hp": 80}}}),
                   row(2, "candidates", [{"id": "a000", "name": "Strike", "action": {"action": "play_card"}},
                                         {"id": "a001", "name": "Defend", "action": {"action": "play_card"}}]),
                   row(3, "model_request", {"questions": {"action": {"criteria": {
                       "a000": {"name": "Strike", "action": {"action": "play_card"}},
                       "a001": {"name": "Defend", "action": {"action": "play_card"}}}}}}),
                   row(4, "model_response", {"response": {"model": "jev", "answers": {"action": {
                       "choice": "a001", "confidence": .73, "probabilities": {"a000": .13, "a001": .87}}}}}))
            feed = TraceFeed(trace=path)
            self.assertEqual(feed.snapshot()["status"], "jev_responded")
            selected = row(5, "selected", {"id": "a001", "name": "Defend", "action": {"action": "play_card"}})
            append(path, selected, complete=False)
            self.assertIsNone(feed.snapshot()["latest"])
            with path.open("ab") as file:
                file.write(b"\n")
            snapshot = feed.snapshot()
            self.assertEqual(snapshot["latest"]["source"], "Jev")
            self.assertEqual(snapshot["latest"]["confidence"], .73)
            self.assertEqual([(o["id"], o["probability"]) for o in snapshot["latest"]["options"]],
                             [("a001", .87), ("a000", .13)])
            append(path, row(6, "action_result", {"status": "completed"}))
            self.assertEqual(feed.snapshot()["latest"]["state"], "accepted")
            append(path, row(7, "before", {"state": {"screen": "MAP", "run": {"floor": 6}}}),
                   row(8, "candidates", [{"id": "a000", "name": "唯一道路", "action": {"action": "choose_map_node"}}]),
                   row(9, "selected", {"id": "a000", "name": "唯一道路", "action": {"action": "choose_map_node"}}))
            latest = feed.snapshot()["latest"]
            self.assertEqual(latest["source"], "Automatic")
            self.assertIsNone(latest["confidence"])
            self.assertIsNone(latest["options"][0]["probability"])

    def test_astra_escalation_uses_latest_observed_state(self):
        projection = Projection()
        projection.new_segment("a/decisions.jsonl")
        projection.consume(row(0, "after", {"state": {"screen": "COMBAT", "turn": 3, "run": {"floor": 17, "current_hp": 9}}}))
        projection.consume(row(1, "expert_required", {"reason": "low_hp_before_spending_energy"}))
        latest = projection.snapshot("live")["latest"]
        self.assertEqual(latest["source"], "Astra requested")
        self.assertEqual(latest["context"]["hp"], 9)
        self.assertIsNone(latest["confidence"])

    def test_failed_jev_request_replaces_stale_action_without_fabricating_probabilities(self):
        projection = Projection()
        projection.new_segment("a/decisions.jsonl")
        projection.consume(row(1, "selected", {"id": "a000", "name": "old action", "action": {"action": "end_turn"}}))
        projection.consume(row(2, "action_result", {"status": "completed"}))
        projection.consume(row(3, "before", {"state": {"screen": "COMBAT", "turn": 3, "run": {"floor": 5}}}))
        projection.consume(row(4, "candidates", [{"id": "a001", "name": "Strike", "action": {"action": "play_card"}}]))
        projection.consume(row(5, "model_request", {"questions": {"action": {"criteria": {
            "a001": {"name": "Strike", "action": {"action": "play_card"}}}}}}))
        thinking = projection.snapshot("live")["current"]
        self.assertEqual(thinking["state"], "pending")
        self.assertIsNone(thinking["confidence"])
        projection.consume(row(6, "model_failure", {"error": "URLError"}))
        projection.consume(row(7, "failure", {"error": "URLError: DNS unavailable"}))
        projection.consume(row(8, "summary", {"status": "error"}))
        snapshot = projection.snapshot("live")
        self.assertEqual(snapshot["latest"]["label"], "old action")
        self.assertEqual(snapshot["current"]["label"], "Jev 请求失败")
        self.assertEqual(snapshot["current"]["state"], "failed")
        self.assertEqual(snapshot["current"]["context"]["floor"], 5)
        self.assertIsNone(snapshot["current"]["options"][0]["probability"])

    def test_expert_action_uses_action_label_and_victory_context(self):
        projection = Projection()
        projection.new_segment("a/decisions.jsonl")
        projection.consume(row(1, "before", {"state": {"screen": "GAME_OVER", "game_over": {"is_victory": True},
                                                       "run": {"current_hp": 0, "max_hp": 83}}}))
        projection.consume(row(2, "expert_decision", {"action": {"action": "continue_game_over"},
                                                     "reason": "Very long state-bound explanation"}))
        latest = projection.latest
        self.assertEqual(latest["label"], "继续胜利结算")
        self.assertTrue(latest["context"]["is_victory"])
        self.assertEqual(latest["reason"], "Very long state-bound explanation")

    def test_stale_and_uncertain_actions_are_not_reported_as_executed(self):
        projection = Projection()
        projection.new_segment("a/decisions.jsonl")
        projection.consume(row(1, "before", {"state": {"screen": "COMBAT"}}))
        projection.consume(row(2, "selected", {"id": "a000", "name": "Strike", "action": {"action": "play_card"}}))
        projection.consume(row(3, "stale_proposal_discarded", {}))
        self.assertEqual(projection.latest["state"], "discarded")
        projection.consume(row(4, "before", {"state": {"screen": "COMBAT"}}))
        projection.consume(row(5, "selected", {"id": "a000", "name": "Defend", "action": {"action": "play_card"}}))
        projection.consume(row(6, "mcp_transport_failure", {}))
        self.assertEqual(projection.latest["state"], "delivery_unknown")

    def test_latest_native_segment_follows_run_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments = [f"00000000-0000-0000-0000-{i:012d}" for i in range(1, 5)]
            for segment, run_id, scope in ((segments[0], "RUN", "native_complete_run"),
                                           (segments[1], "OTHER", "native_complete_run"),
                                           (segments[2], "RUN", "complete_run")):
                path = root / segment / "decisions.jsonl"
                path.parent.mkdir()
                append(path, row(0, "manifest", {"scope": scope, "config": {"expected_run_id": run_id}}))
            first = root / segments[0] / "decisions.jsonl"
            append(first, row(1, "before", {"state": {"screen": "MAP"}}),
                   row(2, "selected", {"id": "a000", "name": "first", "action": {"action": "choose_map_node"}}))
            feed = TraceFeed(game_run_id="RUN", root=root)
            self.assertEqual(feed.snapshot()["latest"]["label"], "first")
            second = root / segments[3] / "decisions.jsonl"
            second.parent.mkdir()
            append(second, row(0, "manifest", {"scope": "native_complete_run", "config": {"expected_run_id": "RUN"}}),
                   row(1, "before", {"state": {"screen": "EVENT"}}),
                   row(2, "selected", {"id": "a000", "name": "second", "action": {"action": "choose_event_option"}}))
            snapshot = feed.snapshot()
            self.assertEqual(snapshot["latest"]["label"], "second")
            self.assertEqual([d["label"] for d in snapshot["history"]], ["second", "first"])
            self.assertNotEqual(snapshot["history"][0]["key"], snapshot["history"][1]["key"])
            replay_fixture = root / "e050-replay" / "decisions.jsonl"
            replay_fixture.parent.mkdir()
            append(replay_fixture, row(0, "manifest", {"scope": "native_complete_run", "config": {"expected_run_id": "RUN"}}))
            self.assertEqual(feed.snapshot()["segment"], segments[3])

    def test_server_exposes_projection_only_and_no_write_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "segment" / "decisions.jsonl"
            path.parent.mkdir()
            append(path, row(0, "manifest", {"scope": "native_complete_run", "config": {"expected_run_id": "RUN"},
                                              "secret": "PRIVATE_SENTINEL"}),
                   row(1, "before", {"state": {"screen": "EVENT", "secret": "PRIVATE_SENTINEL"}}),
                   row(2, "expert_required", {"reason": "<script>alert(1)</script>"}))
            server = serve(TraceFeed(trace=path), port=0)
            self.assertEqual(server.server_address[0], "127.0.0.1")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/state") as response:
                    body = response.read().decode()
                    self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
                self.assertNotIn("PRIVATE_SENTINEL", body)
                self.assertIn("<script>alert(1)</script>", body)
                with urlopen(f"http://127.0.0.1:{server.server_port}/monitor.js") as response:
                    script = response.read().decode()
                self.assertIn("textContent", script)
                self.assertNotIn("innerHTML", script)
                with self.assertRaises(HTTPError) as failure:
                    urlopen(Request(f"http://127.0.0.1:{server.server_port}/api/state", data=b"x", method="POST"))
                self.assertEqual(failure.exception.code, 405)
                with self.assertRaises(HTTPError) as wrong_host:
                    urlopen(Request(f"http://127.0.0.1:{server.server_port}/api/state", headers={"Host": "attacker.example"}))
                self.assertEqual(wrong_host.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
