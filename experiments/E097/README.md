# E097 — one Jev choice per Boss room

Issue: [#187](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/187). Depends on the four independently repeatable E096 winners.

Hypothesis: Jev can reproduce demonstrated winning policies by choosing a policy once at Boss entry from a compact library, while deterministic code performs all numerical execution. This is recipe transfer on familiar states, **not** per-card Jev play or new-state strategy discovery.

Fixed inputs: all four successful E096 A10 entries, v0.111.0, identical frozen commands and entry hashes. [policy-bank.json](policy-bank.json) freezes five policy definitions (four E096 winners plus original/no potions) and one common compact lesson bank. The model sees current entry state, policy definitions and (coached arm only) these lessons; no seed, entry hash, expected answer, future state, raw action tape, or search results. The lessons deliberately describe successful known deck/boss patterns: this is training-set reproduction, not a holdout. Private entry payloads are recovered from E096 raw traces and must match published entry hashes before model use.

Arms: unguided Jev, coached Jev, exact-entry deterministic winning-policy lookup. Each Jev arm makes three fresh requests per case with fixed candidate permutations (seed 9700 + case index × 10 + repetition); the two arms share each permutation. No request cache. Then play the complete real Boss battle with the selected policy. Four cases × two Jev arms × three repetitions + four controls = 28 battles. Four workers; max 300 decisions/180 seconds each; shared budget 60 attempted requests/$0.05, unknown usage counted conservatively. No online Astra interventions or engine rollback search in student execution.

Gate: 12/12 coached clears, at least 10/12 exact teacher-policy selections, all 28 fresh entry/trace audits, budget respected. Report confidence as model answer confidence, **not** win probability. Keep deterministic lookup as the strongest reproduction baseline. Teacher discovery expense is an offline cost and must not be compared as if it recurred on every future battle; the actual marginal cost comparator is lookup. No default promotion or full-run claim.

Commands after committing code: `python3 -m unittest discover -s tests -q`; `python3 -m scripts.evaluate_student_e097 > artifacts/e097-stdout.log 2>&1`.
