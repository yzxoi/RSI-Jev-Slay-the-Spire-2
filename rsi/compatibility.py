"""E001: natural opening plus first combat, five characters at ascension 10."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from .engine import ROOT, CHARACTERS, Headless, first_action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="compat_001")
    parser.add_argument("--ascension", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    batch = str(uuid.uuid4())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    original = ROOT / "vendor/sts2-cli/lib/sts2.dll.original"
    manifest = {"batch_id": batch, "commit": commit, "dependencies": json.loads((ROOT / "dependencies.json").read_text()),
                "original_game_dll_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                "seed": args.seed, "ascension": args.ascension, "results": []}
    for character in CHARACTERS:
        directory = ROOT / "artifacts/runs" / batch / character
        start = time.monotonic()
        result = {"character": character, "status": "error", "steps": 0}
        engine = None
        state = {}
        try:
            engine = Headless(directory)
            state = engine.send({"cmd": "start_run", "character": character, "ascension": args.ascension, "seed": args.seed})
            in_battle = False
            for step in range(400):
                result["steps"] = step
                decision = state.get("decision")
                if decision == "game_over":
                    result["status"] = "normal_defeat" if not state.get("victory") else "victory"
                    break
                if in_battle and decision not in ["combat_play", "card_select"]:
                    result["status"] = "battle_completed"
                    break
                in_battle |= decision == "combat_play"
                state = engine.send(first_action(state))
            else:
                raise TimeoutError("400-step compatibility cap")
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if engine:
                engine.close()
        result.update(seconds=round(time.monotonic() - start, 3), hp=state.get("player", {}).get("hp"),
                      final_decision=state.get("decision"), trace_path=str(directory.relative_to(ROOT)))
        wire = directory / "wire.jsonl"
        if wire.exists():
            result["trace_sha256"] = hashlib.sha256(wire.read_bytes()).hexdigest()
        manifest["results"].append(result)
        print(json.dumps(result), flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    if any(r["status"] == "error" for r in manifest["results"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
