# E121: faithful and faster pre-room restoration

Issue: [#232](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/232). PR: [#235](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/235). Status: fidelity passed; **both performance promotion gates failed**. Preserve validation tools, snapshots and all timing evidence; no automatic accelerator enabled. Baseline: E120's canonical start_run + legal-action prefix, historical game v0.111.0 and the same ten first-elite entries. The original protocol and explicit later timing amendment follow.

## Hypothesis and boundaries

A checkpoint captured on a real map boundary before entering combat can preserve observations and future RNG while removing most prefix replay cost. Never use a mid-combat save's coordinate rollback as an exact snapshot. No HP, rewards, cards, victory flags or RNG edits. No model calls, live-game writes or policy-strength claim.

## Fixed protocol

1. **Preflight, all ten E120 cases, two workers.** A: fresh canonical full prefix. B: fresh prefix stopping before its final select_map_node, require map_select / room_type=Map, write_continue_save, then enter the room. C: new process load that unedited file, compare map state, take the same freshly legal entry action, compare combat entry. Compare exact exported JSON hashes, retain field-level differences. A/B must also match the original E120 entry hash. Run all ten even if an earlier case fails. 20 seconds per subprocess path. Any mismatch prevents promotion, including a map mismatch even if combat later matches. Keep diagnostic downstream reads/actions separate from passing evidence.
2. **Continuation gate, only after preflight passes.** Use all 30 E120 control/flat/UCT selected paths (even duplicate plans). Independently reconstruct A without a save call, verify every old path boundary, and extend with fixed E120 macro/control choices through rewards and the next combat's round-2 opening, or game_over. Capture up to 80 extension actions / 30 seconds per source run. A pending generated-card selection is not a victory. Freeze and commit these exact action/hash sequences before B/C replay.
3. B repeats canonical prefix, saves at the real map boundary, then follows each frozen continuation. C loads the checkpoint in a fresh process and follows each continuation three times. Verify every before/after observation, selected-plan terminal outcome, rewards, next-room state and initial next-turn draws. Each subprocess path: 30 seconds / frozen continuation length. Errors and incomplete cases are distinct from battle losses. All 30 × (B + 3 C) paths remain in the report, including unstarted work after a source failure.
4. Record exact code and DLL hashes, commands, raw trace/save hashes, restoration and execution timings. Checkpoint creation cost is reported separately and amortized explicitly. At least 2× faster restoration and 100% passing selected compatibility paths are required for enabling the opt-in accelerator. Observational parity on this bank does not prove universal engine fidelity or hidden-state completeness.

If the existing loader fails, retain the failed result, diagnose the first divergent fields, and commit each narrowly scoped repair before rerunning all ten preflight cases and the continuation gate. Do not relax the comparison silently. Any normalization needs a separately documented rationale and evaluation; gameplay-relevant differences remain failures. Preserve original game DLLs and old headless build locally; only source patches are tracked.

## Follow-on search

Only after this gate passes, use a separate experiment issue/branch/PR to compare larger flat-MC/UCT budgets. Freeze its budget, RNG replicates and decision rule before execution. Keep the search algorithm/rollout/utility unchanged while measuring the restoration speedup; do not combine an engine-fidelity fix with a new reward heuristic.

## Iteration log

1. Initial preflight harness and protocol, before engine changes. Ten source map boundaries were inspected read-only: all are genuine Map rooms (floors 8 or 6). Save/restore parity has not yet been assumed.
2. Preflight SHA `a96fd8b`: all ten A/B/C entry checks matched exactly; 30 trace triples audited, three synthetic helper tests passed. Existing loader, **no engine edits or normalization**. Full-prefix restoration took 2.76–4.01 s; fresh-process checkpoint restoration took 1.06–1.16 s. Evidence: `preflight-v1.json`; command `python3 scripts/validate_checkpoints_e121.py preflight --output artifacts/runs/e121-preflight-v1.json`. This passes only the entry gate, not future-state fidelity. Add the continuation capture/replay harness, commit it, then capture all 30 references. C reuses each case's unchanged preflight snapshot across all three path families; B independently tests the save-call side effect along each frozen path.
3. Reference-capture SHA `15e108e`: four helper tests passed; all 30 source continuations matched their E120 battle paths and completed their fixed extension. Commit the full `continuations.json` bank before replay. No engine patch was needed. The source bank includes defeats (which correctly have no post-death extension), not just surviving runs.
4. Continuation-validation SHA `367916e`: all **120/120** B/C paths matched, including 90 restored paths (three repetitions of each control/flat/UCT plan). Sources stopped at the next combat's second-turn opening in 26 cases and legitimate death in four; source extensions contained 253 actions. No engine edits, ignored fields, state normalization or RNG changes. `verification-v1.json` preserves the complete result. Median restoration ratio was **2.76×**, but the implementation's strict *minimum individual ratio >=2* performance gate failed: minimum 0.52×. Two C loads took 5.38/3.17 seconds. One neighboring ordinary B reconstruction took 8.15 seconds; wire timestamps locate the slow operations in load_save (5.23/3.01 s) and start_run initialization (6.06 s), respectively. Cause is not established. Do not claim the original performance gate passed.

### Preregistered timing replication after the failed minimum-speed gate

The original timing denominator was measured in an earlier reference-capture batch, while the gate used the slowest later C sample. This cannot establish a guaranteed per-load speedup on a shared desktop. **Before new measurements**, replace that performance claim with a robust paired experiment: the same ten cases, five fresh A/C pairs per case, order alternating by `(case_index + repetition) % 2`, two case workers, no repetitions selected or removed. All 100 entry states must still match exactly; the complete 120-path fidelity gate remains mandatory and unchanged.

Report each of the 50 paired ratios, per-case median ratios, pooled median ratio, and A/C median, nearest-rank p95 and maximum elapsed restore time. The amended performance gate requires **every case's median ratio >=2**, pooled paired median >=2, and checkpoint p95 no worse than full-prefix p95. Retain all outliers. This amendment is post-hoc to v1 and tests a practical typical/tail-cost criterion, not the original guarantee for every load. If the fresh paired batch fails, do not automatically repeat or enable acceleration. Command: `python3 scripts/validate_checkpoints_e121.py timing --output artifacts/runs/e121-timing-v2.json`.

## Final evidence and decision

Timing replication tested SHA **`76ad2fa`**; original fidelity validation tested SHA **`367916e`**. The fresh paired batch completed once in 117.64 seconds. All 50 pairs / 100 map and combat-entry comparisons matched exactly. No samples were discarded and no engine source/binary was changed.

| Timing measure | Full prefix A | Map snapshot C |
| --- | ---: | ---: |
| Median restore seconds | 3.234 | 1.117 |
| Nearest-rank p95 seconds | 3.749 | 3.471 |
| Maximum seconds | 5.037 | 4.238 |

Median paired speedup: **2.737×**. Nine per-case median ratios exceeded 2×, but Defect-a was **1.495×**, so the amended promotion gate also **failed**. The three slow Defect-a loads were 3.447, 2.244 and 3.813 seconds; its other two were 1.078 and 1.125. We do not identify the cause or relabel this as a pass. The first batch's minimum individual ratio failure also remains visible in `verification-v1.json`.

The complete evidence includes 30 preflight paths, 30 reference continuations, 120 continuation checks and 100 paired timing paths: **280 raw trace/wire/stderr triples**. All exported-state fidelity checks passed, including rewards and subsequent draws on 26 surviving reference paths; four reference paths ended in legitimate death. These repeated paths are compatibility evidence, not independent game wins or proof that every future branch restores faithfully. Snapshots remain unedited and local/ignored.

**Decision:** merge the opt-in validators and evidence; do not enable checkpoint restoration in the default controller or claim a stable >=2× guarantee. `verified-checkpoints.json` binds the ten snapshots to their prefix/map/entry hashes, engine hashes and evidence hashes, and explicitly marks `performance_promotion_pass: false`. It certifies the tested fidelity scope, not speed promotion.

A separate, amended-before-testing **E124 / [#236](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/236)** may deliberately consume these *unpromoted research snapshots* to test end-to-end useful search under a fixed 120-second budget. This withdraws E124's initial proposed speed-promotion prerequisite explicitly; it does not satisfy or change E121's failed gates. It must retain the failures/slow loads, reproduce every first-24 trajectory against E120, and verify final plans by full-prefix replay. That bounded research comparison, not another timing retry, addresses the actual decision of whether more search quality is obtained within the deadline.

```bash
python3 -m unittest discover -s tests -p 'test_checkpoints.py' -v
python3 scripts/validate_checkpoints_e121.py freeze --output experiments/E121/continuations.json
# Commit the complete frozen bank before B/C replay.
python3 scripts/validate_checkpoints_e121.py verify --output artifacts/runs/e121-verify-v1.json
```
