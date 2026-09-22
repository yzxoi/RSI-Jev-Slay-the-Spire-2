"""Reproducible opening-combat experiments; the game loop runs without Astra."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import time
import uuid
from .engine import ROOT, CHARACTERS, Headless, first_action
from .jev import Budget, Jev
from .policy import combat_candidates, model_state
from .trace import Trace, digest, version_manifest


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)] if values else None


def episode(config, manifest, jev=None):
    run_id = str(uuid.uuid4())
    directory = ROOT / "artifacts/runs" / run_id
    trace = Trace(directory, {**manifest, **config, "run_id": run_id, "scope": "first_natural_combat"})
    engine = None
    started = time.monotonic()
    state = {}
    result = {**config, "run_id": run_id, "status": "error", "steps": 0, "model_calls": 0,
              "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "initial_hp": None}
    latencies = []
    try:
        engine = Headless(directory)
        state = engine.send({"cmd": "start_run", "character": config["character"], "ascension": config["ascension"], "seed": config["seed"]})
        entered = False
        for step in range(config.get("max_steps", 400)):
            result["steps"] = step
            decision = state.get("decision")
            if decision == "game_over":
                result["status"] = "normal_defeat" if not state.get("victory") else "victory"
                break
            if entered and decision not in ["combat_play", "card_select"]:
                result["status"] = "battle_completed"
                break
            if not entered and decision == "combat_play":
                entered = True
                result["initial_hp"] = state["player"]["hp"]
                result["initial_state_hash"] = digest(state)
            trace.write("before", {"state": state, "state_hash": digest(state)})
            if decision == "combat_play":
                candidates = combat_candidates(state)
                trace.write("candidates", candidates)
                if config["policy"] == "first" or len(candidates) == 1:
                    selected = candidates[0]
                else:
                    selected, call = jev.choose(model_state(state), candidates, trace)
                    result["model_calls"] += 1
                    latencies.append(call["seconds"])
                    for metric in ["input_tokens", "output_tokens"]:
                        result[metric] += call["usage"].get(metric, 0)
                    result["cost_usd"] += call["usage"].get("cost", 0)
                command = selected["action"]
                trace.write("selected", selected)
            else:
                command = first_action(state)
                trace.write("selected", {"action": command, "source": "fixed_preamble_or_selection"})
            state = engine.send(command)
            trace.write("after", {"state": state, "state_hash": digest(state)})
        else:
            raise TimeoutError("Episode step limit")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        trace.write("failure", {"error": result["error"]})
    finally:
        if engine:
            engine.close()
    result.update(final_hp=state.get("player", {}).get("hp"), final_decision=state.get("decision"),
                  final_state_hash=digest(state), seconds=round(time.monotonic() - started, 3),
                  model_p50_seconds=percentile(latencies, .5), model_p95_seconds=percentile(latencies, .95))
    if result["initial_hp"] is not None and result["final_hp"] is not None:
        result["net_hp_lost"] = result["initial_hp"] - result["final_hp"]
    trace.write("summary", result)
    result["trace_path"] = str(trace.path.relative_to(ROOT))
    result["trace_sha256"] = trace.close()
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--characters", default=",".join(CHARACTERS))
    parser.add_argument("--seeds", default="trace_001")
    parser.add_argument("--policies", default="first,jev")
    parser.add_argument("--ascension", type=int, default=10)
    parser.add_argument("--max-calls", type=int, default=200)
    parser.add_argument("--max-usd", type=float, default=.25)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    chars, policies = args.characters.split(","), args.policies.split(",")
    if set(chars) - set(CHARACTERS) or set(policies) - {"first", "jev"}:
        parser.error("Unsupported character or policy")
    manifest = version_manifest()
    if manifest["tracked_dirty"]:
        raise RuntimeError("Commit implementation changes before evaluation")
    budget = Budget(args.max_calls, args.max_usd)
    jev = Jev(budget) if set(policies) - {"first"} else None
    configs = [{"character": char, "seed": seed, "ascension": args.ascension, "policy": policy}
               for seed in args.seeds.split(",") for char in chars for policy in policies]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda c: episode(c, manifest, jev), configs))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"manifest": manifest, "configuration": vars(args), "results": results,
                                 "budget": {"requests": budget.calls, "cost_usd": budget.spent, "usage_unknown": budget.unknown}}, indent=2) + "\n")
    if any(r["status"] == "error" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
