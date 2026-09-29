## Hypothesis
A bounded portfolio evaluated with the pinned, patched real-game CLI can improve unseen Act 1 completion over our practical deterministic beam planner with early potions, without any model calls. This tests online planning, not replaying a teacher's recorded solution.

## Fixed evaluation
- Five characters: Ironclad, Silent, Defect, Regent, Necrobinder; A0.
- Two unused seeds: `e115_act1_20260929_a`, `e115_act1_20260929_b`; all 10 pairs reported.
- Control: current trigger/retaliation-aware beam planner plus E096 early-potion rule.
- Treatment: six deterministic tactical policies; independent CLI continuation to battle end, rank clear first, then HP + 6 per remaining potion; choose one next legal action, validate actual transition, refresh at turn/draw/selection boundaries.
- Shared macro: existing fixed route/rest/event/card policy; claim potions if space, skip if full; leave shops. Macro strength is explicitly outside this hypothesis.
- Resources enabled in canonical and branch engines. Replay the complete actual prefix; verify entry digest; carry real inventory. No game-state edits, fabricated rewards or rollback-selected canonical victories.
- Limits: 150 actions / 15 seconds per branch; 36 comparison batches / 180 probes / 360 search seconds per run; 420 seconds / 1,500 canonical actions per run. Two concurrent episodes, three branch workers each. At the fixed search cap use the control and count degraded decisions. A deadline or engine stall is not a loss or a win.
- Zero API requests; raw canonical and speculative traces separate, hashes published.

## Decision rule
First run the `a` cohort for compatibility, then the unchanged `b` cohort only if no canonical error, replay mismatch or invalid action. Preserve failed iterations. Promote playing-strength claims only if all 10 pairs are valid, treatment gains at least two additional Act 1 clears and no more than one paired regression, with no replay/transition mismatch. Otherwise retain an opt-in diagnostic prototype only if correctness checks pass; do not change live defaults. Small sample is exploratory; Act 1 clears are not full-run wins.

## Scope
No external solver integration, model router, snapshot implementation, live gameplay or macro-policy changes in this experiment. Measure prefix replay time separately to inform the next experiment.

## Implementation contract

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/220

`rsi/engine_search.py` is opt-in and has no live MCP or model access. The controller compares `control`, `reserve`, `defend`, `focus`, `develop`, and `draw`. Their approximate scores nominate actions only; complete CLI battle continuations determine ranking. The reserve value of six HP per remaining potion is an explicit heuristic, not an established exchange rate or probability. No incomplete continuation can be labelled a clear. Defeat branches are ranked by last observed enemy HP, then rounds survived; this does not claim those branches become survivable.

Each canonical action is selected from fresh legal choices. Exact predicted suffixes can be reused within a turn only when both the entire actual command-prefix hash and current state digest match. The chosen action's actual transition must match the branch; mismatch stops that canonical run as an error. A new turn, drawn/generated card, or selection interface refreshes comparison. Agreement between every proposal takes the common action without a speculative call. Prefixes preserve inventory and RNG-consuming history; no hidden-state edits or state-only cache are used. Entry observation equality and checked transitions are evidence for these runs, not proof that the engine exposes all hidden state.

Search caps cause an explicit counted control-policy fallback. Branch timeouts/action caps are retained as incomplete results and excluded from ranking; branch engine errors fail the correctness gate. Baseline and treatment share all macro choices, but different HP/inventory can naturally cause the same fixed rules to choose different routes or rest actions. Shops are left without purchases, ordinary rewards take the first card, potions are claimed if a slot is free; this isolates combat at the cost of an intentionally limited whole-run macro policy.

## Reproduction and iteration log

1. Commit implementation and this protocol before running any checks.
2. Run synthetic boundary/cache/deadline tests plus existing teacher/resource/planner tests.
3. Run cohort `a`. Only a correctness pass permits the unchanged `b` cohort. Report every selected character even on error; never silently replace an input.

```sh
python3 -m unittest discover -s tests -p 'test_engine_search.py' -v
python3 -m scripts.evaluate_engine_search_e115 --cohort a --output experiments/E115/iteration1-a.json
python3 -m scripts.evaluate_engine_search_e115 --cohort b --output experiments/E115/iteration1-b.json
```

The run manifest records the exact tested code SHA, original/patched game and headless assembly hashes, patch hashes, dependency revision, policies and budgets. Raw traces live under ignored `artifacts/runs/`; compact result files include their SHA-256 hashes. All outcomes here are offline CLI Act 1 results, never native game/full-run victories. Runtime targets the retained v0.111.0 CLI, not the currently installed public game.

### Iteration 1 — implementation `ad78b3c`

Synthetic checks: 8/8 new tests, plus 4 teacher, 6 resource and 2 planner regression tests passed. Cohort a launched with the command above. While it runs, a separate saved-trace auditor is added: it verifies trace/wire/stderr hashes, tested SHA, candidate membership, actual canonical prefix provenance, and every accepted prediction against its source speculative trace. This does not alter the already-running controller or its configuration.

Auditor iteration: `e7b7073` failed an interim integrity check with `IndexError` on a branch whose remaining budget expired before the engine greeting, leaving zero commands. This is an incomplete branch, not a win or a controller failure. The auditor now accepts empty-command traces only for timeout/error with zero replay/actions/entry, and a synthetic regression rejects labelling the same trace as a clear. Controller code and the ongoing evaluation are unchanged.

## Result and exit decision — 2026-09-29

**Do not promote; close PR #221 without merging.** The prototype and all failed evidence stay on `codex/e115-engine-lookahead`. The correctness gate failed, so cohort b is **not started**, rather than silently removed or treated as losses. Its ten planned arm/character cells are explicit in [decision.json](decision.json). No default or live controller changed.

Tested controller SHA: `ad78b3c`. Original DLL: `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`. Exact patched DLL, assembly, dependency and patch versions are in [iteration1-a.json](iteration1-a.json). The independent auditor was corrected at `de69bfd`; 9 synthetic tests plus the 12 previously passing related regressions cover its contract. No model requests were made by the experiment.

| Character / seed a / A0 | Control | Search | Comparison |
| --- | --- | --- | --- |
| Ironclad | Defeat, floor 12 | Defeat, floor 12 | Tie |
| Silent | Defeat, floor 12 | Defeat, floor 12 | Tie |
| Defect | Defeat, floor 17 | CLI selection error, floor 17, last observed HP 26 | Invalid pair |
| Regent | Defeat, floor 17 | Defeat, floor 17 | Tie |
| Necrobinder | Defeat, floor 12 | Defeat, floor 12 | Tie |

There are **zero canonical Act 1 clears**. Search produced 735 speculative branches: 686 battle clears, 24 defeats, 23 timeouts and 2 engine errors. These 686 clears are repeated local continuations, not independent battles won by the agent and not canonical run victories. 712 entries were verified. All 485 checked canonical predictions matched their branch transition; that does not negate the failures before entry or the late canonical selector failure.

The full saved-evidence audit passed: 10 canonical traces / 1,849 transitions, 735 speculative traces / 9,050 transitions, complete trace/wire/stderr hash checks, actual-prefix provenance and prediction-source verification. This proves integrity of the recorded evidence, **not** compatibility or simulator correctness. Command:

```sh
python3 -m scripts.audit_engine_search_e115 experiments/E115/iteration1-a.json \
  --output experiments/E115/audit-iteration1-a.json
```

The batch took 1,036.1 seconds wall time with two episode workers. Summed episode time was 57.9 seconds for control versus 1,756.7 seconds for search (30.3×); 91.3% of summed branch time was prefix recovery. These are measurements under this local concurrent workload, not portable performance guarantees. The first budget fallback occurred at floors 8/11/11/13 for Ironclad/Silent/Defect/Regent. Necrobinder died before exhausting its budget. **No Boss decision received an engine comparison**; only Regent and Necrobinder reached an elite with search available. This tests a poor search-allocation policy and cannot establish the upper bound of real-engine planning.

### What failed, and the next smaller experiments

1. **Repeated search spends the budget before the important rooms.** An already computed clearing continuation is currently reconsidered after every turn/draw; budget exhaustion can then discard it for the legacy policy. [Proposal #224](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/224) isolates reusing and verifying a computed battle plan, without a snapshot implementation or additional model calls.
2. **A chained card selection can disappear.** Defect used Duplicator then Acrobatics. After the first discard, stderr recorded a second nine-option selection, but CLI timed out waiting for an actionable boundary. Source inspection suggests that `ResolvePending` completes the old task and then clears a reentrantly created new request. [E117 / #223](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/223) records the frozen failure and proposed narrow compatibility test; the mechanism is not yet experimentally confirmed. The initial E116 label was corrected because a separate parallel experiment already reserved that number.
3. **Prefix replay still has rare execution failures.** One branch failed at map entry with an already-completed task error; another encountered an invalid card index during prefix replay. Both were excluded from outcome scoring and retained as errors. [Diagnosis #226](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/226) isolates these failures; fixing the selector alone would not certify them resolved.

The common macro still takes the first offered reward and leaves shops. Policy diversity is also limited: all six share the same selection heuristic. These limits constrain overall strength; adding Jev/Astra before measuring the revised search and execution reliability would obscure attribution. No claim of cheaper autonomous winning play is justified by this iteration.
