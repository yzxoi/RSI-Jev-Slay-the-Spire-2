# E097 — one Jev choice per Boss room

Issue: [#187](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/187). Depends on the four independently repeatable E096 winners.

Hypothesis: Jev can reproduce demonstrated winning policies by choosing a policy once at Boss entry from a compact library, while deterministic code performs all numerical execution. This is recipe transfer on familiar states, **not** per-card Jev play or new-state strategy discovery.

Fixed inputs: all four successful E096 A10 entries, v0.111.0, identical frozen commands and entry hashes. [policy-bank.json](policy-bank.json) freezes five policy definitions (four E096 winners plus original/no potions) and one common compact lesson bank. The model sees current entry state, policy definitions and (coached arm only) these lessons; no seed, entry hash, expected answer, future state, raw action tape, or search results. The lessons deliberately describe successful known deck/boss patterns: this is training-set reproduction, not a holdout. Private entry payloads are recovered from E096 raw traces and must match published entry hashes before model use.

Arms: unguided Jev, coached Jev, exact-entry deterministic winning-policy lookup. Each Jev arm makes three fresh requests per case with fixed candidate permutations (seed 9700 + case index × 10 + repetition); the two arms share each permutation. No request cache. Then play the complete real Boss battle with the selected policy. Four cases × two Jev arms × three repetitions + four controls = 28 battles. Four workers; max 300 decisions/180 seconds each; shared budget 60 attempted requests/$0.05, unknown usage counted conservatively. No online Astra interventions or engine rollback search in student execution.

Gate: 12/12 coached clears, at least 10/12 exact teacher-policy selections, all 28 fresh entry/trace audits, budget respected. Report confidence as model answer confidence, **not** win probability. Keep deterministic lookup as the strongest reproduction baseline. Teacher discovery expense is an offline cost and must not be compared as if it recurred on every future battle; the actual marginal cost comparator is lookup. No default promotion or full-run claim.

Commands after committing code: `python3 -m unittest discover -s tests -q`; `python3 -m scripts.evaluate_student_e097 > artifacts/e097-stdout.log 2>&1`.

## Result and decision

Tested code `1756c7188a54c4a73ee5fa11316232c75ba416ce`; 131 tests passed before execution. Exact command: `python3 -m scripts.evaluate_student_e097 > artifacts/e097-stdout.log 2>&1`. Model returned `typesafe/jev-1.13-20260917`; actual engine/dependency/patch hashes and all model answers, including probabilities/confidence, are recorded in [result.json](result.json) and hashed local traces.

| Arm | Boss clears | Exact teacher policy | Exact teacher trajectory | Model spend |
| --- | --- | --- | --- | --- |
| Exact-entry lookup | 4/4 | 4/4 | 4/4 | $0 |
| Jev without lesson bank | 2/12 | 2/12 | 2/12 | $0.002196810 |
| Jev with lesson bank | **12/12** | **12/12** | **12/12** | **$0.002307186** |

All 28 episodes ended normally. All 28 fresh Boss-entry checks passed; ten additional raw-trace audit checks passed on every episode, including real combat boundaries, policy binding, legal candidates, wire/trajectory hashes, no debug commands, and no model requests during battle. The model made 24 fresh paid requests (24 distinct request hashes), zero unknown-cost or retried calls, total $0.004503996. Total evaluation wall time 63.332 seconds with four workers. Recheck local evidence using `python3 -m scripts.audit_student_e097`; summary in [audit.json](audit.json).

The coached arm used **one request per battle**, averaging $0.000192266 and 1.020 seconds (median 1.018). It required zero online Astra decisions and no engine branching. These costs exclude offline Astra authoring and E096 teacher discovery. We have **not** shown lower marginal cost than deterministic lookup: lookup is free of model requests and also reproduces every solved entry. The 924.623 seconds of E096 search is a one-time discovery expense, not a recurring teacher inference cost.

Unguided Jev cleared Ceremonial Beast twice, but failed all Kin cases and one Ceremonial repetition. Even changing candidate order changed some choices. The common lesson bank selected all four correct policies on every repetition, including Necrobinder's delayed potion schedule. This supports bounded recipe transfer, not independent strategy discovery or confidence calibration.

**Decision: merge opt-in reproduction evaluator and compact lesson bank; do not change the production policy.** The preregistered gate passes. The useful architecture is now explicit: expensive teacher discovery/verification → versioned strategy memory → exact lookup when covered, or a bounded Jev policy choice → deterministic fresh-state execution. We still need to test strategy selection on unseen entries, detect coverage failures and route those to the teacher, validate on current Steam, and demonstrate full-run wins including reward/draft/path decisions. The 12 student wins are repeated known Boss states, not 12 independent full runs.
