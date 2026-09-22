"""Bounded JSON-line transport to the pinned headless game engine."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ["Ironclad", "Silent", "Defect", "Regent", "Necrobinder"]


class Headless:
    def __init__(self, directory: Path, timeout=30):
        directory.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.stderr = (directory / "engine.stderr.log").open("w")
        self.wire = (directory / "wire.jsonl").open("w")
        sdk = ROOT / ".tools/dotnet"
        engine = ROOT / "vendor/sts2-cli"
        env = dict(os.environ, DOTNET_ROOT=str(sdk), STS2_GAME_DIR=str(engine / "lib"),
                   DOTNET_CLI_TELEMETRY_OPTOUT="1")
        assembly = engine / "src/Sts2Headless/bin/Debug/net9.0/Sts2Headless.dll"
        self.proc = subprocess.Popen([str(sdk / "dotnet"), str(assembly)],
                                     cwd=engine, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=self.stderr, text=True, bufsize=1)
        self.responses = queue.Queue()
        def collect():
            for line in self.proc.stdout:
                self.responses.put(line)
            self.responses.put(None)
        threading.Thread(target=collect, daemon=True).start()
        try:
            ready = self.read()
            if ready.get("type") != "ready":
                raise RuntimeError(f"Unexpected engine greeting: {ready}")
        except Exception:
            self.close()
            raise

    def record(self, kind, value):
        self.wire.write(json.dumps({"time": time.time(), "kind": kind, "data": value}, ensure_ascii=False) + "\n")
        self.wire.flush()

    def read(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                line = self.responses.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError("Headless response deadline exceeded") from None
            if line is None:
                raise RuntimeError("Headless process closed stdout")
            if line.startswith("{"):
                result = json.loads(line)
                self.record("state", result)
                if result.get("type") == "error":
                    raise RuntimeError(result.get("message", "Unknown headless error"))
                return result
            if time.monotonic() >= deadline:
                raise TimeoutError("Headless produced no JSON response before deadline")

    def send(self, command):
        self.record("command", command)
        self.proc.stdin.write(json.dumps(command) + "\n")
        self.proc.stdin.flush()
        return self.read()

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.stderr.close()
        self.wire.close()


def action(name, **args):
    return {"cmd": "action", "action": name, "args": args}


def first_action(state):
    """Deliberately simple execution baseline; no claims of playing strength."""
    decision = state.get("decision")
    if decision == "combat_play":
        for card in state.get("hand", []):
            if card.get("can_play"):
                args = {"card_index": card["index"]}
                if card.get("target_type") == "AnyEnemy":
                    enemies = state.get("enemies", [])
                    if not enemies:
                        continue
                    args["target_index"] = enemies[0]["index"]
                return action("play_card", **args)
        return action("end_turn")
    if decision == "event_choice":
        opts = [o for o in state.get("options", []) if not o.get("is_locked")]
        return action("choose_option", option_index=opts[0]["index"]) if opts else action("leave_room")
    if decision == "map_select":
        choices = state.get("choices", [])
        if not choices:
            raise RuntimeError("No map choices")
        node = next((c for c in choices if c["type"] == "Monster"), choices[0])
        return action("select_map_node", col=node["col"], row=node["row"])
    if decision == "card_reward":
        return action("skip_card_reward")
    if decision == "bundle_select":
        return action("select_bundle", bundle_index=0)
    if decision == "card_select":
        minimum = state.get("min_select", 1)
        return action("select_cards", indices=",".join(str(c.get("index", i)) for i, c in enumerate(state.get("cards", [])[:minimum]))) if minimum else action("skip_select")
    if decision == "rest_site":
        opts = [o for o in state.get("options", []) if o.get("is_enabled", True)]
        if opts:
            opt = next((o for o in opts if o.get("option_id") == "HEAL"), opts[0])
            return action("choose_option", option_index=opt["index"])
    if decision == "shop":
        return action("leave_room")
    raise RuntimeError(f"Unsupported baseline decision: {decision}")
