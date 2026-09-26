# E103 — verify missed defense at proposed end-turns

Issue #198, preregistered 2026-09-26 before checker implementation or new engine execution. The question is whether bounded engine verification adds value over a simple arithmetic diagnostic, and whether this can identify future escalation opportunities without spending Astra calls.

## Inputs, baseline and intervention

Freeze **all five** E102 before-states in which Jev actually selected end_turn with positive energy: Silent baseline turns 3/4 and dynamic turns 4/5/7. They share the historical A10 e093_resources_002 Kin Priest entry; these are development mechanism cases, not independent seeds or battle wins. [inputs.json](inputs.json) contains full states/hashes, the accepted continuation prefixes, source trace hashes and original observed after hashes. Initial accepted prefixes reference the hash-pinned E099 fixtures. No state editing, future action tape or reward modification.

For each state, replay the actual end_turn as the baseline and require its after hash to match the original E102 transition. Enumerate currently legal basic Defend cards or Survivor in candidate order. A branch plays exactly one such defense, resolves a required Survivor single-card discard from fresh candidates, then ends the turn. Survivor ordinals enumerate the expected remaining hand (fresh engine selection must confirm its shape; a mismatch fails visibly). At most eight alternative branches per input, at most three commands after each entry, at most 60 seconds including accepted-prefix replay per branch. Max four independent CLI processes; no native game writer. Include every error, truncation and unsupported boundary; no selective retry.

Compare actual HP/status at the next player turn, enemies, resources, hand and draw/discard counts. Immediate HP improvement is a local counterfactual result, not proof of an optimal full-run action. Preserve the covered dynamic turn-4 negative control: seven carried Block plus one Plating covers eight incoming, so early end is legitimate for current HP.

Two cheap arithmetic comparators are frozen before evaluation: (1) incoming preview minus current Block, (2) the same plus exported Plating at end of turn. Each estimates the benefit of the best supported block preview; neither simulates discard, powers, next draws or delayed value. Record legacy end-turn guard abstentions too, but do not change that guard. Exact-engine verification is a diagnostic only and does not override canonical actions. If arithmetic already identifies the same cases, prefer it as a future inexpensive trigger and measure why/where engine proof is still needed.

## Budget and decision rule

Zero Jev/Astra API calls and zero API spend. Use pinned CLI game v0.111.0, original DLL SHA 9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4; full code/game/patch/.NET manifest in results. Branch wall time is a real cost, reported separately from cheap diagnostic time.

Require exact entries, original baseline after-state parity, fresh legal selections, full trace/wire chain and real next-player/terminal boundary. The two motivating dynamic turn-5/7 missed defenses must be identified and the covered turn-4 control must not claim avoidable immediate HP loss. All five cases and all selected alternatives remain in the report. Passing permits only an opt-in diagnostic/evidence merge; no router threshold or automatic action override promotion. Changed discard/shuffle may harm later play even when HP improves immediately.

A subsequent battle/router experiment needs a separate issue/branch/PR and preregistration with disjoint inputs, contemporary baseline, budgets and no selected reruns. This experiment does not test win rate or confidence calibration.

## Commands

Implementation will provide `python3 -m scripts.evaluate_end_turn_e103` and `python3 -m scripts.audit_end_turn_e103`. Run `python3 -m unittest discover -s tests -q` after committing the implementation and before gameplay. Preserve full raw branches under ignored artifacts/runs; commit compact outcomes, provenance and trace hashes after evaluation.

## Results

Exact tested gameplay SHA **ecb9a08bc2b30d62fd56165a6e7e4a265c0d18b9**. All **148 tests passed** before execution. All five frozen inputs and 17 branches completed normally, with zero errors, truncations or reruns. Five baselines reproduce the original E102 after-state hashes exactly; all 12 alternatives use legal current defense/discard choices and stop at the next player turn. [Results and timing](result.json), [independent trace/source audit](audit.json). No new canonical battle or full-run wins are counted.

| Frozen end-turn state | HP before | Actual end → next HP | Best one-defense alternative → next HP | Verified immediate gain |
| --- | --- | --- | --- | --- |
| Silent static baseline, turn 3 | 57 | 48 | 57 (Survivor); Defend gives 56 | 9 |
| Silent static baseline, turn 4 | 48 | 48 | 48 | 0 |
| Silent dynamic, turn 4 | 59 | 59 | 59 | 0 |
| Silent dynamic, turn 5 | 59 | 42 | 53 (Survivor, all three discards) | 11 |
| Silent dynamic, turn 7 | 29 | 8 | 16 (Defend) | 8 |

The two proposed missed defenses are real local mistakes: +11 and +8 HP in separate counterfactual branches. **Do not add these gains to E102's final 8 HP.** No joint continuation was evaluated, and the accepted action/selection history can change future shuffles even when the next exposed state looks similar. All enumerated alternatives leave next-turn exposed enemies, powers, hand, potion inventory, gold and pile counts unchanged relative to their own baseline; this does not establish equality of unexposed future RNG or discard ordering. Two covered controls give no immediate HP gain from more ordinary defense.

### Cheap calculation versus engine replay

| Diagnostic | Missed-defense false positives / negatives | Exact best HP-gain matches |
| --- | --- | --- |
| Incoming minus current Block | 1 / 0 | 3/5 |
| Also include end-turn Plating | 0 / 0 | 5/5 |

Raw visible arithmetic overstates turn-3 loss by 2 and falsely flags dynamic turn 4, missing the end-turn Block. Adding the already exported Plating amount corrects both. This is a development-set mechanism check on one character/Boss, not general diagnostic accuracy. The unchanged legacy guard abstains on all five inputs because of unknown powers (Minion in every case, Plating or Block Next Turn in some). The result does not authorize removing that guard's unknown-effect checks globally.

The five Plating-aware arithmetic evaluations took **0.018 ms total** inside the calculation function; this excludes loading, parsing and policy/controller overhead and is not a repeated performance benchmark. No Jev/Astra API requests or charges were made. Offline authoring/review in this Codex task remains unmetered.

Seventeen independent engine branches took **40.424 s wall time** with four workers, **138.800 s summed branch wall time**. Per branch: 7.869–8.992 s. Replaying the 225–240 accepted prefix commands took **137.685 s**, about **99.2%** of summed branch time. The remainder includes the actual comparison actions and process teardown; summed branch time is not CPU time. Cold accepted-prefix replay dominates, so this implementation is too expensive to assume free on every end-turn. On these inputs the cheap calculation already gives the same flags and gains.

### Decision and next step

The preregistered gate passes: both motivating errors verified, covered control handled correctly, all 17 entry/legality/wire/hash/boundary audits pass, and the complete five-state selection is independently recovered from all four original E102 traces. Merge the **opt-in diagnostic and evidence**, leaving the production controller unchanged.

Use inexpensive arithmetic as the candidate screening layer in a future experiment. A screened discrepancy should first become a fresh, explicit remaining-turn objective for Jev; exact-engine verification or Astra is justified only when effects are unsupported or the discrepancy remains unresolved. This is a proposed routing design, not a validated decision rule. Test on disjoint seeded trajectories before integrating an automatic override or claiming fewer expert calls. Broad routing remains [#190](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/190); complete-run learning remains [#189](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/189).

Iteration history: `8037671` freezes the protocol and all five inputs before checker implementation; `ecb9a08` implements the comparisons, audits and tests before any branches; `1eb2f22` adds only post-run read-only cost/diagnostic counts. No gameplay code changes or repeated branches during evaluation. Game v0.111.0, .NET SDK 9.0.318, CLI upstream `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`; complete DLL/assembly/patch hashes are in the result manifest. Current Steam compatibility is not established.

Executed commands:
```bash
python3 -m unittest discover -s tests -q
python3 -m scripts.evaluate_end_turn_e103 > artifacts/runs/e103.log 2>&1
python3 -m scripts.audit_end_turn_e103 --source-root /path/to/E102/worktree
```
The last command requires all four original E102 raw traces plus the E103 raw branches. Public fixed inputs contain everything needed to replay the five selected entries from the pinned E099 initial prefixes; they do not need an API key. Traces and engine wire logs stay in local ignored artifacts/runs, with public hashes and complete outcome accounting.
