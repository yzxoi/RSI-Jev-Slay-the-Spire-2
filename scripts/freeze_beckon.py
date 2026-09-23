"""Freeze E054 Soul Fysh decision states from SHA-pinned local native traces."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


SOURCES = (
    ("742313db-2a17-4898-bc5f-da8b2e6e1f5e", "2966da8f067f440aece5c11497090ca30732a243409773f25d66a43d1fbd76c7"),
    ("be84b32b-c9d6-4197-a692-2a9be2ace8f7", "e1287eeec501b94e31b579fba9c63dd981630d164d24f5d89b0a9a8129d5531e"),
    ("aff8d967-1c96-4d17-9c66-05e617cf8a8f", "6cbff3a547f394679c20e18087c9fdd24840b4e23a9f3784c97bbbe388ba3fd9"),
    ("d410c8ec-0887-4c6e-a470-6091628528d4", "ce6a3e17f58a808ecda925690f0b725a4201d8f139fe2efadf1d1ddcca740a15"),
)


def freeze(source_root):
    cases = []
    for segment, expected_sha in SOURCES:
        path = source_root / segment / "decisions.jsonl"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha, path
        pending = None
        for line in path.open():
            record = json.loads(line)
            kind, data = record.get("kind"), record.get("data") or {}
            if kind == "before":
                raw = data.get("state") or {}
                pending = None
                if (raw.get("run_id") == "DCEND0WRAPGL" and raw.get("screen") == "COMBAT"
                        and (raw.get("run") or {}).get("floor") == 17):
                    combat = raw["combat"]
                    pending = {"segment": segment, "source_seq": record["seq"],
                               "state": {"run_id": raw["run_id"], "screen": "COMBAT",
                                         "turn": raw["turn"], "selection": raw.get("selection"),
                                         "run": {"floor": 17, "relics": raw["run"].get("relics", [])},
                                         "combat": {"player": combat["player"], "hand": combat["hand"],
                                                    "enemies": combat["enemies"],
                                                    "end_turn_will_kill_player": combat.get("end_turn_will_kill_player")}}}
            elif kind == "candidates" and pending is not None:
                pending["candidates"] = data
                cases.append(pending)
                pending = None
    assert len(cases) == 57, len(cases)
    return {"schema_version": 1, "kind": "frozen_native_decisions_not_simulated_outcomes",
            "run_id": "DCEND0WRAPGL", "source_hashes": dict(SOURCES), "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True,
                        help="E054 ignored artifacts/runs directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frozen = freeze(args.source_root)
    content = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(content, mtime=0))
    print(json.dumps({"cases": len(frozen["cases"]), "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))
