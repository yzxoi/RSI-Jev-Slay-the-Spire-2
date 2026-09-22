"""Bounded visible native-MCP battle demo. Stops before post-combat choices."""
import argparse
import fcntl
import json
from pathlib import Path
import time
import uuid
from .engine import ROOT
from .jev import Budget, Jev
from .mcp import MCP, live_candidates, stable_fingerprint
from .trace import Trace, version_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080/mcp")
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-actions", type=int, default=80)
    parser.add_argument("--max-seconds", type=int, default=240)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = version_manifest()
    if manifest["tracked_dirty"]:
        raise RuntimeError("Commit implementation before the visible experiment")
    lockpath = ROOT / "artifacts/private/live-control.lock"
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    with lockpath.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run_id = str(uuid.uuid4())
        trace = Trace(ROOT / "artifacts/runs" / run_id, {**manifest, "mode": "native_mcp", "config": vars(args), "run_id": run_id})
        budget = Budget(100, .15)
        result = {"run_id": run_id, "status": "error", "actions": 0, "execution_enabled": args.execute}
        started = time.monotonic()
        raw = {}
        try:
            mcp = MCP(args.url, trace)
            health = mcp.call("health_check")
            if health.get("service") != "sts2-ai-agent" or health.get("play_running") or health.get("status") != "ready":
                raise RuntimeError("Expected a healthy STS2 instance without another autoplay writer")
            result["health"] = {k: health.get(k) for k in ["game_version", "mod_version", "process_id", "instance_role"]}
            raw = mcp.call("get_raw_game_state")
            if raw.get("run_id") != args.expected_run_id or raw.get("screen") != "COMBAT":
                raise RuntimeError("Expected the specifically selected live combat")
            result.update(character=raw["run"]["character_id"], ascension=raw["run"]["ascension"],
                          floor=raw["run"]["floor"], initial_hp=raw["run"]["current_hp"],
                          initial_enemies=[{"id": e["enemy_id"], "hp": e["current_hp"]} for e in raw["combat"]["enemies"]])
            jev = Jev(budget) if args.execute else None
            waits = 0
            while True:
                if raw.get("run_id") != args.expected_run_id:
                    raise RuntimeError("Live run changed; stopped without acting")
                if raw.get("screen") != "COMBAT":
                    result["status"] = "battle_boundary" if raw.get("screen") == "REWARD" else "requires_attention"
                    break
                if time.monotonic() - started > args.max_seconds or result["actions"] >= args.max_actions:
                    raise TimeoutError("Visible demonstration budget reached")
                ready = raw["combat"].get("action_readiness", {}).get("can_use_combat_actions", False)
                if not ready:
                    if raw["combat"].get("action_readiness", {}).get("is_paused"):
                        raise RuntimeError("User paused the game")
                    waits += 1
                    if waits > 6:
                        raise TimeoutError("No actionable combat state")
                    mcp.call("wait_until_actionable", {"timeout_seconds": 10, "raw_state": True})
                    raw = mcp.call("get_raw_game_state")
                    continue
                waits = 0
                candidates = live_candidates(raw)
                if not candidates:
                    raise RuntimeError("No supported combat candidates")
                trace.write("before", {"state": raw, "state_hash": stable_fingerprint(raw)})
                trace.write("candidates", candidates)
                if not args.execute:
                    result.update(status="read_only_ready", candidates=len(candidates))
                    break
                selected = candidates[0] if len(candidates) == 1 else jev.choose(raw.get("agent_view", raw), candidates, trace)[0]
                trace.write("selected", selected)
                fresh = mcp.call("get_raw_game_state")
                if stable_fingerprint(fresh) != stable_fingerprint(raw) or selected["action"] not in [c["action"] for c in live_candidates(fresh)]:
                    trace.write("stale_proposal_discarded", {"before": stable_fingerprint(raw), "after": stable_fingerprint(fresh)})
                    raw = fresh
                    continue
                if selected["action"]["action"] == "end_turn" and fresh["combat"].get("end_turn_will_kill_player"):
                    raise RuntimeError("Lethal end-turn choice requires expert review")
                # Readiness and the competing writer are checked again after inference.
                if mcp.call("health_check").get("play_running"):
                    raise RuntimeError("Another autoplay writer became active")
                command = {**selected["action"], "raw_state": True,
                           "reason": f"程序摘要：Jev 选择 {selected['name']}；回合 {fresh['turn']}，能量 {fresh['combat']['player']['energy']}。"}
                answer = mcp.call("act", command)
                result["actions"] += 1
                trace.write("action_result", answer)
                raw = mcp.call("get_raw_game_state")
                trace.write("after", {"state": raw, "state_hash": stable_fingerprint(raw)})
                print(json.dumps({"step": result["actions"], "action": selected["name"], "screen": raw.get("screen"),
                                  "turn": raw.get("turn"), "hp": (raw.get("run") or {}).get("current_hp")}, ensure_ascii=False), flush=True)
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            trace.write("failure", {"error": result["error"]})
        result.update(final_screen=raw.get("screen"), final_hp=(raw.get("run") or {}).get("current_hp"),
                      seconds=round(time.monotonic() - started, 3), model_calls=budget.calls,
                      cost_usd=budget.spent, usage_unknown=budget.unknown)
        trace.write("summary", result)
        result["trace_path"] = str(trace.path.relative_to(ROOT))
        result["trace_sha256"] = trace.close()
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"manifest": manifest, "result": result}, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if result["status"] not in ["read_only_ready", "battle_boundary"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
