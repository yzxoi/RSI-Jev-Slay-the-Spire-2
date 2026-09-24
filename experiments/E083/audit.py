"""Verify the E083 reward table against one ignored E081 native trace."""

import argparse
import hashlib
import json
from pathlib import Path
import re


EXPECTED_SHA256 = "e0fd99e72429c47b2abf1933cc1ef5e11df8fd2436b80ee16fdf6aff89ecd420"
EXPECTED_FLOORS = (2, 3, 5, 8, 9)


def reward_rows(trace: Path) -> list[dict]:
    rows = []
    state = None
    candidates = []
    with trace.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind, data = event["kind"], event["data"]
            if kind == "before":
                state = data["state"]
            elif kind == "candidates":
                candidates = data
            elif kind == "selected" and data.get("name") == "choose_reward_card":
                rows.append(
                    {
                        "floor": state["run"]["floor"],
                        "offers": [
                            candidate["details"]["card_id"]
                            for candidate in candidates
                            if candidate.get("name") == "choose_reward_card"
                        ],
                        "selected": data["details"]["card_id"],
                    }
                )
    return rows


def memo_rows(memo: Path) -> list[dict]:
    rows = []
    for line in memo.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"\| (\d+) \| ([A-Z_, ]+) \| ([A-Z_]+) \|", line)
        if match:
            rows.append(
                {
                    "floor": int(match.group(1)),
                    "offers": [card.strip() for card in match.group(2).split(",")],
                    "selected": match.group(3),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument(
        "--memo",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "docs/research/deck-jobs-v0111.md",
    )
    args = parser.parse_args()
    digest = hashlib.sha256(args.trace.read_bytes()).hexdigest()
    observed = reward_rows(args.trace)
    documented = memo_rows(args.memo)
    passed = (
        digest == EXPECTED_SHA256
        and [row["floor"] for row in observed] == list(EXPECTED_FLOORS)
        and observed == documented
    )
    print(
        json.dumps(
            {
                "trace_sha256": digest,
                "trace_hash_matches": digest == EXPECTED_SHA256,
                "observed": observed,
                "documented": documented,
                "passed": passed,
            },
            indent=2,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
