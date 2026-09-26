## Hypothesis

In four-player combat, a new global turn can be visible before the local player may act. The single-player eight-second quiet-state deadline then stops a healthy co-op controller. In opt-in multiplayer, wait read-only for local action readiness and a stable snapshot, bounded by the controller's overall deadline. Keep single-player settling unchanged.

## Baseline and fixed inputs

E111/#212 on legitimate four-player Steam run `32ASTF9N6E`, local Ironclad A0, game v0.107.1, adapter 0.16.2: 47 accepted local actions and four acknowledged map votes across two segments, followed by two eight-second `Native turn did not settle` timeouts. In the second timeout's 45 probes, `can_use_combat_actions` remained false. Neither timeout sent an action. Trace hashes: `634f3cc260157319230fe494859d26c6a44ae530855a53786ce565a5aa1cb532`, `913d2e3c746a4f1544a343e82b10d46d22bc947e62b8058fdac68564dcff4042`. The host later abandoned the run at floor 13; this was not a natural defeat.

The offline evaluation uses synthetic four-player combat states with an unready phase lasting more than eight seconds, followed by a stable local-ready state, plus identity loss, scene change, and the overall deadline. This is a controller-mechanics regression, not gameplay strength evidence. A future live evaluation uses the same E111 controller flags and a new actual run ID only if a new lobby exists.

## Decision rule

Multiplayer must send zero actions while local readiness is false, resume from a fresh stable snapshot after more than eight seconds, and stop on run/ownership loss or the overall deadline. Single-player settle tests must still pass. Report real four-player continuation separately with tested SHA, accepted actions, stalls, trace hash, model cost and actual game outcome. Without a new live lobby, leave live efficacy unverified and do not merge on synthetic evidence alone.
