# E134 — Audited full-prefix reset routing

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/252

Status: preregistered; waiting for complete E133 v1 certificate before recovery evaluation.

## Motivation and scoped objective

E133's expanded natural pool exposed native-save mismatches that E132's five entries did not cover. Examples: train-044-b2 loads the same visible Map but the selected Unknown node yields This or That? instead of the original Fuzzy Wurm Crawler combat; train-019-b5 reproduces its Elite battle and rewards, then the next Unknown node yields Shop instead of Monster. Root cause in saved hidden state / adapter reinitialization is not yet established. No engine/RNG/state patch here.

A failed native reset must not enter PPO training. Preserve the complete E133 v1 certification, stop its training gate, and test a conservative frozen reset routing certificate: use native saves only where all original continuation checks passed; retain every incompatible entry using independently verified full-prefix replay. This is infrastructure compatibility, not a new model-strength experiment or evidence that native save fidelity passes globally.

## Fixed inputs and evaluation

After E133 v1 certification finishes, commit its whole report and SHA before any E134 evaluation. Inputs are the unchanged E133 264-seed bank and every failed train/validation certification record, selected exhaustively by status rather than success or reward; record their case IDs and proof file hash. Reuse original passing certificates with an immutable source reference and raw-hash audit; do not rerun native restoration to pick a lucky success.

A fallback candidate is eligible only when its original full-prefix PPO control reached a legitimate terminal, the independent full-prefix-plus-save B continuation matched and extended to next-combat second turn or real death, and native C failed. Reconstruct the complete frozen B action/hash path from its hashed wire, removing only the write_continue_save protocol message, and verify the reconstructed path/final hash against the original report. Reconstruct the original A battle path similarly against its transition hash. Any source/prefix/trace disagreement or another failure class blocks the combined certificate.

For each eligible failure: two independent fresh-process full-prefix replays of the entire B path (including rewards/next draws), plus one full-prefix PPO episode replay of the entire A battle. No save/load command in these replay runs. Require every before/after/entry/final hash and outcome exact. Max 30 s per path; 8 workers; total recovery phase <=300 s, no automatic retries. All failures/caps/unstarted records retained. This preserves all E133 training states and rewards; only their reset cost changes.

## Routing gate and integration

Only if every previously passing certificate re-audits, every failed case is eligible and all three fallback replays match, export a new certificate containing all original records/provenance and a fixed per-case restore mode. Failed native save records stay explicitly failed in the nested source evidence. E133's loader must require this protocol, exhaustive case coverage and bound recovery evidence; a runtime mismatch never silently falls back. Native mode still uses per-call file/engine/map/entry validation; verified full-prefix cases pass no snapshot to the existing PPO episode function.

E133 v2 may resume training on exactly its frozen samples, model/seeds/episodes/rewards/selection/test gates using this new certificate after a public protocol amendment and commit. No sample exclusion, HP edit, win claim or engine fix. Do not change E133 v1's failed gate. Held-out test certification remains deferred until weight hashes are committed; the same deterministic routing policy and recovery checks apply to any later test-only native failure before comparing learned policies, with all failures retained.

## Exit and records

Failure of any source/fallback/runtime consistency check blocks training/test; report it rather than removing the entry. Publish code SHA, exact input hashes/cases, commands, measured modes and all trace hashes. Raw native saves/traces stay ignored. One separate PR for this compatibility fix, based on the E133 branch; merge into that branch only after the routing gate passes. True native Unknown-node restoration remains an open follow-up, not solved by this routing experiment.
