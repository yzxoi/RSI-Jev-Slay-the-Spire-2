"""Read-only localhost window for append-only Jev/Astra decision traces."""

import argparse
from collections import deque
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import urlsplit

from .engine import ROOT


STATIC = Path(__file__).parent / "monitor_static"
VISIBLE_EVENTS = {
    "manifest", "before", "candidates", "planning", "model_request",
    "model_response", "model_failure", "selected", "expert_required",
    "expert_decision", "room_opening_proposed", "floor_plan", "room_plan",
    "action_result", "explicit_rejection", "after", "failure", "summary",
}


def _short(value, limit=180):
    return str(value or "")[:limit]


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1 else None


def _label(candidate):
    details = candidate.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    action = candidate.get("action") or {}
    title = next((details[k] for k in ("title", "name", "card_name", "label") if isinstance(details.get(k), str) and details[k]), None)
    name = title or candidate.get("name") or action.get("action") or "Unknown action"
    suffix = []
    for key, label in (("target_index", "target"), ("option_index", "option"), ("card_index", "card")):
        if key in action:
            suffix.append(f"{label} {action[key]}")
    return _short(name, 80) + (" · " + ", ".join(suffix) if suffix else "")


def _context(raw):
    state = raw.get("state", raw) if isinstance(raw, dict) else {}
    run = state.get("run") or {}
    context = state.get("context") or {}
    player = (state.get("combat") or {}).get("player") or state.get("player") or {}
    return {
        "screen": _short(state.get("screen") or state.get("decision"), 40),
        "floor": run.get("floor", context.get("floor")),
        "turn": state.get("turn", state.get("round")),
        "hp": run.get("current_hp", player.get("hp")),
        "max_hp": run.get("max_hp", player.get("max_hp")),
        "run_id": state.get("run_id"),
    }


class Projection:
    """Project raw rows to a small, non-sensitive decision view."""

    def __init__(self):
        self.history = deque(maxlen=16)
        self.latest = None
        self.pending = {}
        self.plan = None
        self.status = "waiting"
        self.segment = None
        self.game_run_id = None
        self.last_time = None
        self.error = None
        self.events = 0
        self.last_context = {}

    def new_segment(self, path):
        self.segment = Path(path).parent.name
        self.pending = {}
        self.plan = None
        self.status = "segment_changed"
        self.error = None
        self.last_context = {}

    def _options(self, selected_id=None, model_only=False):
        choices = (self.pending.get("model_candidates") if model_only else self.pending.get("candidates")) or []
        answer = self.pending.get("answer") or {}
        probabilities = answer.get("probabilities") or {}
        if not isinstance(probabilities, dict):
            probabilities = {}
        options = [{"id": c.get("id"), "label": _label(c),
                    "probability": _number(probabilities.get(c.get("id"))),
                    "selected": c.get("id") == selected_id} for c in choices if isinstance(c, dict)]
        if any(o["probability"] is not None for o in options):
            options.sort(key=lambda o: (o["probability"] is None, -(o["probability"] or 0)))
        total = len(options)
        shown = options[:60]
        if selected_id and not any(o["selected"] for o in shown):
            chosen = next((o for o in options if o["selected"]), None)
            if chosen:
                shown[-1:] = [chosen]
        return shown, total

    def _publish(self, decision):
        decision["key"] = f"{self.segment}:{decision.get('seq')}"
        self.latest = decision
        self.history.appendleft(decision)

    def consume(self, row):
        kind = row.get("kind")
        data = row.get("data")
        self.events += 1
        self.last_time = row.get("time")
        if kind == "manifest":
            manifest = data or {}
            self.game_run_id = (manifest.get("config") or {}).get("expected_run_id") or manifest.get("game_run_id") or self.game_run_id
        elif kind in ("floor_plan", "room_plan"):
            data = data or {}
            self.plan = {"kind": kind, "floor": data.get("floor", data.get("start_floor")),
                         "guidance": _short(data.get("guidance"), 360)}
            self.game_run_id = data.get("run_id") or self.game_run_id
        elif kind == "before":
            self.pending = {"context": _context(data or {}), "candidates": []}
            self.last_context = self.pending["context"]
            self.game_run_id = self.pending["context"].get("run_id") or self.game_run_id
            self.status = "observing"
        elif kind == "candidates":
            self.pending["candidates"] = data if isinstance(data, list) else []
            self.status = "candidates_ready"
        elif kind == "planning":
            self.pending["planning"] = True
        elif kind == "model_request":
            criteria = ((((data or {}).get("questions") or {}).get("action") or {}).get("criteria") or {})
            self.pending["model_candidates"] = [{"id": key, **value} for key, value in criteria.items() if isinstance(value, dict)] if isinstance(criteria, dict) else []
            self.pending["answer"] = {}
            self.pending["model_pending"] = True
            self.status = "jev_thinking"
        elif kind == "model_response":
            response = (data or {}).get("response") or {}
            answer = (response.get("answers") or {}).get("action") or {}
            self.pending["answer"] = answer
            self.pending["model"] = _short(response.get("model"), 80)
            self.pending["model_pending"] = False
            self.status = "jev_responded"
        elif kind == "model_failure":
            self.error = _short((data or {}).get("error"), 100)
            self.status = "model_failure"
        elif kind == "room_opening_proposed":
            self.pending["astra_opening"] = True
        elif kind == "expert_decision":
            self.pending["expert"] = data or {}
            action = self.pending["expert"].get("action") or {}
            options, total = self._options()
            self._publish({"seq": row.get("seq"), "time": self.last_time,
                           "context": self.pending.get("context") or {}, "source": "Astra",
                           "label": _short(self.pending["expert"].get("reason") or action.get("action"), 120),
                           "confidence": None, "options": options, "option_count": total,
                           "state": "proposed", "plan": self.plan})
            self.status = "astra_decided"
        elif kind == "expert_required":
            reason = _short((data or {}).get("reason"), 120)
            options, total = self._options()
            self._publish({"seq": row.get("seq"), "time": self.last_time,
                           "context": self.last_context, "source": "Astra requested",
                           "label": reason, "confidence": None, "options": options,
                           "option_count": total, "state": "awaiting_astra", "plan": self.plan})
            self.status = "astra_requested"
        elif kind == "selected":
            selected = data or {}
            chosen_id = selected.get("id")
            answer = self.pending.get("answer") or {}
            model_match = chosen_id is not None and answer.get("choice") == chosen_id
            source = ("Astra" if self.pending.get("expert") else
                      "Astra room plan" if self.pending.get("astra_opening") else
                      "Jev" if model_match else
                      "Computed" if self.pending.get("planning") else "Automatic")
            options, total = self._options(chosen_id if model_match else None, model_only=model_match)
            if not model_match:
                for option in options:
                    option["probability"] = None
                    option["selected"] = option["id"] == chosen_id
            self._publish({"seq": row.get("seq"), "time": self.last_time,
                           "context": self.pending.get("context") or {}, "source": source,
                           "model": self.pending.get("model") if model_match else None,
                           "label": _label(selected), "confidence": _number(answer.get("confidence")) if model_match else None,
                           "options": options, "option_count": total, "state": "proposed", "plan": self.plan})
            self.status = "action_proposed"
        elif kind == "action_result":
            if self.latest and self.latest["state"] == "proposed":
                self.latest["state"] = "accepted" if (data or {}).get("status") in ("completed", "accepted", "success") else "result_received"
                self.status = self.latest["state"]
        elif kind == "explicit_rejection":
            if self.latest and self.latest["state"] == "proposed":
                self.latest["state"] = "rejected"
            self.status = "rejected"
        elif kind == "after":
            self.last_context = _context(data or {})
        elif kind == "failure":
            self.error = _short((data or {}).get("error"), 160)
            self.status = "failure"
        elif kind == "summary":
            summary = data or {}
            self.status = _short(summary.get("status") or "completed", 60)

    def snapshot(self, mode):
        current = None
        if self.status in {"observing", "candidates_ready", "jev_thinking", "jev_responded"}:
            answer = self.pending.get("answer") or {}
            choice_id = answer.get("choice") if self.status == "jev_responded" else None
            model_only = bool(self.pending.get("model_candidates"))
            options, total = self._options(choice_id, model_only=model_only)
            selected = next((option for option in options if option["selected"]), None)
            current = {"context": self.pending.get("context") or {},
                       "source": "Jev" if self.pending.get("model_pending") or choice_id else "Controller",
                       "label": selected["label"] if selected else ("Jev 正在评估…" if self.pending.get("model_pending") else "准备候选选项…"),
                       "model": self.pending.get("model"),
                       "confidence": _number(answer.get("confidence")) if choice_id else None,
                       "options": options, "option_count": total, "state": "proposed" if selected else "pending",
                       "plan": self.plan}
        return {"mode": mode, "status": self.status, "game_run_id": self.game_run_id,
                "segment": self.segment, "plan": self.plan, "latest": self.latest,
                "current": current, "history": list(self.history), "last_time": self.last_time,
                "error": self.error, "events": self.events}


class TraceFeed:
    def __init__(self, *, trace=None, game_run_id=None, replay_trace=None, replay_interval=0.25, root=None):
        self.root = Path(root or ROOT / "artifacts/runs")
        self.trace = Path(trace) if trace else None
        self.game_run_id = game_run_id
        self.replay_trace = Path(replay_trace) if replay_trace else None
        self.replay_interval = replay_interval
        self.projection = Projection()
        self.lock = threading.Lock()
        self.path = None
        self.offset = 0
        self.partial = b""
        self.manifest_cache = {}
        self.replay_rows = None
        self.replay_started = None
        self.replay_index = 0

    def _matches(self, path):
        if path not in self.manifest_cache:
            try:
                with path.open("rb") as file:
                    manifest = json.loads(file.readline()).get("data") or {}
                self.manifest_cache[path] = (
                    manifest.get("scope", "").startswith("native"),
                    (manifest.get("config") or {}).get("expected_run_id") or manifest.get("game_run_id") or manifest.get("run_id"))
            except (OSError, ValueError):
                return False
        native, run_id = self.manifest_cache[path]
        return native and (not self.game_run_id or run_id == self.game_run_id)

    def _latest_path(self):
        if self.trace:
            return self.trace
        paths = (p for p in self.root.glob("*/decisions.jsonl") if self._matches(p))
        return max(paths, key=lambda p: p.stat().st_mtime_ns, default=None)

    def _consume_line(self, line):
        try:
            row = json.loads(line)
            if isinstance(row, dict) and row.get("kind") in VISIBLE_EVENTS:
                self.projection.consume(row)
        except (ValueError, TypeError) as exc:
            self.projection.error = f"Invalid complete trace row: {type(exc).__name__}"
            self.projection.status = "trace_error"

    def _poll_file(self):
        path = self._latest_path()
        if path is None or not path.exists():
            return
        if path != self.path or path.stat().st_size < self.offset:
            self.path, self.offset, self.partial = path, 0, b""
            self.projection.new_segment(path)
        with path.open("rb") as file:
            file.seek(self.offset)
            chunk = file.read()
            self.offset = file.tell()
        if not chunk:
            return
        lines = (self.partial + chunk).split(b"\n")
        self.partial = lines.pop()
        for line in lines:
            if line:
                self._consume_line(line)

    def _poll_replay(self):
        if self.replay_rows is None:
            self.projection.new_segment(self.replay_trace)
            self.replay_rows = []
            with self.replay_trace.open("rb") as file:
                for line in file:
                    row = json.loads(line)
                    if row.get("kind") in VISIBLE_EVENTS:
                        self.replay_rows.append(row)
            self.replay_started = time.monotonic()
        target = min(len(self.replay_rows), 1 + int((time.monotonic() - self.replay_started) / self.replay_interval))
        while self.replay_index < target:
            self.projection.consume(self.replay_rows[self.replay_index])
            self.replay_index += 1

    def snapshot(self):
        with self.lock:
            if self.replay_trace:
                self._poll_replay()
                mode = "replay"
            else:
                self._poll_file()
                mode = "live"
            result = self.projection.snapshot(mode)
            if self.replay_trace:
                result["replay_progress"] = [self.replay_index, len(self.replay_rows)]
            return result


def serve(feed, host="127.0.0.1", port=8765):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/state":
                body = json.dumps(feed.snapshot(), ensure_ascii=False).encode()
                content_type = "application/json; charset=utf-8"
            elif path in ("/", "/monitor.css", "/monitor.js"):
                filename = "monitor.html" if path == "/" else path[1:]
                body = (STATIC / filename).read_bytes()
                content_type = {"monitor.html": "text/html", "monitor.css": "text/css", "monitor.js": "text/javascript"}[filename] + "; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.send_error(405)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Decision window: http://{host}:{server.server_port}/", flush=True)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--trace", help="Pin one decisions.jsonl file")
    source.add_argument("--replay-trace", help="Replay a saved trace without touching the game")
    parser.add_argument("--game-run-id", help="Follow the newest native trace segment for this game run")
    parser.add_argument("--replay-interval", type=float, default=0.25, help="Seconds per relevant record")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open a 460x760 Chrome app window")
    args = parser.parse_args()
    if args.replay_interval <= 0:
        parser.error("--replay-interval must be positive")
    feed = TraceFeed(trace=args.trace, game_run_id=args.game_run_id,
                     replay_trace=args.replay_trace, replay_interval=args.replay_interval)
    server = serve(feed, port=args.port)
    if args.open:
        subprocess.Popen(["open", "-na", "Google Chrome", "--args",
                          f"--app=http://127.0.0.1:{server.server_port}/",
                          "--window-size=460,760"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
