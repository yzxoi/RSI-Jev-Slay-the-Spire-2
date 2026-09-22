"""Append-only local evidence, with hashes suitable for committed summaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from .engine import ROOT


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def version_manifest():
    return {"schema_version": 1,
            "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "tracked_dirty": bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip()),
            "dependencies": json.loads((ROOT / "dependencies.json").read_text()),
            "game_dll_sha256": hashlib.sha256((ROOT / "vendor/sts2-cli/lib/sts2.dll.original").read_bytes()).hexdigest()}


class Trace:
    def __init__(self, directory, manifest):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "decisions.jsonl"
        self.file = self.path.open("x")
        self.seq = 0
        self.write("manifest", manifest)

    def write(self, kind, data):
        self.file.write(json.dumps({"seq": self.seq, "time": time.time(), "kind": kind, "data": data}, ensure_ascii=False) + "\n")
        self.file.flush()
        self.seq += 1

    def close(self):
        self.file.close()
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
