## Hypothesis

In four-player combat, a new global turn can be visible before the local player may act. The single-player eight-second quiet-state deadline then stops a healthy co-op controller. In opt-in multiplayer, wait read-only for local action readiness and a stable snapshot, bounded by the controller's overall deadline. Keep single-player settling unchanged.

## Baseline and fixed inputs

E111/#212 on legitimate four-player Steam run `32ASTF9N6E`, local Ironclad A0, game v0.107.1, adapter 0.16.2: 47 accepted local actions and four acknowledged map votes across two segments, followed by two eight-second `Native turn did not settle` timeouts. In the second timeout's 45 probes, `can_use_combat_actions` remained false. Neither timeout sent an action. Trace hashes: `634f3cc260157319230fe494859d26c6a44ae530855a53786ce565a5aa1cb532`, `913d2e3c746a4f1544a343e82b10d46d22bc947e62b8058fdac68564dcff4042`. The host later abandoned the run at floor 13; this was not a natural defeat.

The offline evaluation uses synthetic four-player combat states with an unready phase lasting more than eight seconds, followed by a stable local-ready state, plus identity loss, scene change, and the overall deadline. This is a controller-mechanics regression, not gameplay strength evidence. A future live evaluation uses the same E111 controller flags and a new actual run ID only if a new lobby exists.

## Decision rule

Multiplayer must send zero actions while local readiness is false, resume from a fresh stable snapshot after more than eight seconds, and stop on run/ownership loss or the overall deadline. Single-player settle tests must still pass. Report real four-player continuation separately with tested SHA, accepted actions, stalls, trace hash, model cost and actual game outcome. Without a new live lobby, leave live efficacy unverified and do not merge on synthetic evidence alone.

## Offline result, 2026-09-26

Tested clean implementation SHA `55125c69b4ac82a9b042e36bfcd3d3c603dc46e9` with Python 3.13.5:

```bash
python3 -m unittest discover -s tests -q
git diff --check
```

All 160 tests passed, including six new co-op turn tests. The fixed synthetic sequence kept the local player unready for more than eight simulated seconds while peer state changed, then returned a stable local-ready state without any `act` call. Separate cases covered partial readiness, run/local identity loss, scene change and the overall time boundary. The single-player quiet-state settle tests also passed. This shows controller behavior only; it does not establish that a long real peer action will eventually finish or that the adapter's readiness signal will recover.

The actual game was read-only checked after the fix: it was at `MAIN_MENU` with `run_unknown`, so no matching four-player run was available. The old overlay was stopped because it was pinned to the abandoned run. No live action, Jev call, Astra call, game result or new trace was produced by E112. Compact results are in [result.json](result.json).

**Decision:** keep the PR open for a new co-op lobby. Do not merge as a validated live compatibility fix yet. When a new run exists, use its actual ID, enforce one local writer, record exact code SHA, and publish its continuation result in a PR comment before deciding whether to merge or close.
