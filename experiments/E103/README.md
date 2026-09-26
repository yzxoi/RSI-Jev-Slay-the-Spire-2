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
