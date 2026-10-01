# E121: faithful and faster pre-room restoration

Issue: [#232](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/232). Status: protocol frozen before testing. Baseline: E120's canonical start_run + legal-action prefix, historical game v0.111.0 and the same ten first-elite entries.

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
