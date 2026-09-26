## Hypothesis
A co-op map action should be offered to the local AI only after at least one peer vote is visible and no local vote is recorded. After submitting exactly one vote, the controller should require an observed local vote or real room transition before considering the action complete. This will prevent the E110 duplicated map call and still let the team set its route.

## Baseline and fixed inputs
E110/#210 tested SHA 1b64546 on real four-player Steam run 32ASTF9N6E: two `choose_map_node` calls returned completed while local_vote stayed null, vote_count 0 and map row unchanged. The repeat guard stopped before a third. Continue only that legitimate run if present, starting around floor 6; same v0.107.1 E106/E109 adapter, four players, local Ironclad A0. Use the same Jev controller and pinned E050 overlay. This is exploratory stateful continuation, not an A/B win-rate comparison. No raw player identifiers or proprietary binaries in Git.

## Decision rule
The controller must never repeat an unacknowledged map vote. It must wait when peer votes are absent or local vote is already recorded, and stop with trace on an unacknowledged submission after a bounded read-only wait. Require unchanged local ownership, fresh indices and single local writer throughout. Stop at victory/defeat, user stop, ownership ambiguity, uncertain action delivery, unsupported shared state or the overall E110 resource cap; report all outcomes. All code changes are committed before execution and every segment's trace hash/result is published in the PR. The adapter itself is unchanged in this experiment.

## Real run result, 2026-09-26

Tested clean gameplay SHA `81b94633a3b823ab7ca85037f117d17d4348929a` against the same live four-player Steam run `32ASTF9N6E`, local Ironclad A0, game v0.107.1 and the E106/E109 installed adapter. The seed was not exposed. E050's read-only overlay remained pinned to this run on Built-in Retina Display, source SHA `d800be43c2510a95912d7b29a573044a125226a6`. `python3 -m unittest discover -s tests -q` passed 154 tests and `git diff --check` passed before execution.

Both sequential segments used the same committed code and this command, changing only `segment01.json` to `segment02.json` after a verified no-action-sent wait timeout:

```bash
python3 -m rsi.campaign --expected-run-id 32ASTF9N6E \
  --require-local-multiplayer --expected-player-count 4 --execute \
  --combat-policy retaliate --auto-combat-selections --guard-exhaust-selection \
  --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop \
  --max-actions 200 --max-seconds 900 --max-usd 0.20 \
  --output artifacts/runs/E111/segment01.json
```

Segment 1 accepted 34 local actions, including three map votes each followed by an observed `local_vote` acknowledgement, and reached floor 12 combat. It used nine Jev requests costing $0.002502276; trace SHA-256 `634f3cc260157319230fe494859d26c6a44ae530855a53786ce565a5aa1cb532`. Segment 2 resumed from a fresh actionable state, accepted 13 local actions and one acknowledged map vote, reached floor 13 combat, and used three Jev requests costing $0.000809046; trace SHA-256 `913d2e3c746a4f1544a343e82b10d46d22bc947e62b8058fdac68564dcff4042`. Both ended with `Native turn did not settle before deadline; no action sent`: the single-player quiet-state probe timed out after 8 seconds while peers were acting. Neither segment recorded an explicit rejection, uncertain action delivery, duplicate vote, defeat or victory. Four acknowledgement events establish that the new route rule worked in these observed rooms, not a general win-rate gain.

**Decision:** merge the opt-in multiplayer vote gate and acknowledgement requirement, which stopped the E110 duplicate-vote failure in this same run. The new independent blocker is co-op turn settling; issue E112 will replace whole-party quiet-state waiting with the MCP's local-action readiness gate. Do not promote the controller as a complete multiplayer policy yet. Compact outcomes are in [result.json](result.json), ignored raw traces in `artifacts/runs/`.
