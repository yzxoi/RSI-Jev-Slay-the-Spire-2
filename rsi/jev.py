"""Typed Jev decisions with explicit request and spend budgets."""
import json
from pathlib import Path
import threading
import time
import urllib.request
from .engine import ROOT

MODEL = "typesafe/jev-1.13"
ENDPOINT = "https://openrouter.ai/api/v1/systemone"


def read_key():
    import os
    key = os.environ.get("OPENROUTER_RSI_JEV_KEY")
    if key:
        return key
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip().startswith("OPENROUTER_RSI_JEV_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("OPENROUTER_RSI_JEV_KEY is missing")


class Budget:
    # Upper input estimate at the pinned model's 32K limit and published price.
    # The provider's reported cost remains authoritative; unknown usage stops calls.
    reserve_usd = 32000 * 0.042 / 1_000_000

    def __init__(self, max_calls=200, max_usd=0.25):
        self.max_calls, self.max_usd = max_calls, max_usd
        self.calls = 0
        self.spent = 0.0
        self.reserved = 0.0
        self.unknown = False
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            if self.unknown or self.calls >= self.max_calls or self.spent + self.reserved + self.reserve_usd > self.max_usd:
                raise RuntimeError("Jev budget exhausted or usage unknown")
            self.calls += 1
            self.reserved += self.reserve_usd

    def settle(self, usage):
        with self.lock:
            self.reserved -= self.reserve_usd
            cost = usage.get("cost")
            if not isinstance(cost, (int, float)) or cost < 0:
                self.unknown = True
            else:
                self.spent += cost


class Jev:
    def __init__(self, budget):
        self.key = read_key()
        self.budget = budget

    def choose(self, state, candidates, trace):
        body = {"model": MODEL, "state": state, "questions": {"action": {
            "type": "choice",
            "instructions": "Choose the action that best preserves the chance to win the entire Slay the Spire 2 run. Consider action order, enemy threats, future turns, card/power/relic effects and resources. Use the supplied current rules rather than memories of another game version. The engine will observe the result and decide again after this one action. End turn only when further plays are worse. Candidate numeric features, when present, are limited estimates, not full simulations.",
            "criteria": {c["id"]: {k: v for k, v in c.items() if k != "id"} for c in candidates}}}}
        trace.write("model_request", body)
        self.budget.acquire()
        started = time.monotonic()
        try:
            request = urllib.request.Request(ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode(),
                       headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=25) as response:
                result = json.load(response)
        except Exception as exc:
            self.budget.settle({})
            trace.write("model_failure", {"error": type(exc).__name__, "message": str(exc).replace(self.key, "[redacted]")})
            raise
        elapsed = time.monotonic() - started
        self.budget.settle(result.get("usage", {}))
        trace.write("model_response", {"response": result, "seconds": elapsed})
        selected = result.get("answers", {}).get("action", {}).get("choice")
        candidate = next((c for c in candidates if c["id"] == selected), None)
        if candidate is None:
            raise ValueError("Jev returned a choice outside the candidate set")
        return candidate, {"usage": result.get("usage", {}), "seconds": elapsed,
                           "answer": result["answers"]["action"], "model": result.get("model")}
