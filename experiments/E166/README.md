# E166 — typed Ashwater selection, fixed battle counterfactuals

Issue #320. E165's Boss trace exhausted valuable cards because a destructive
selection was ranked as acquisition. Test only an opt-in source-ID-based Ashwater
polarity correction with fewer removals on value ties; retain all other card,
potion timing and macro rules. Unknown/generation contexts keep original behavior.
Default FrozenProgram and live controller stay unchanged.

Before testing, freeze three E165 natural entries: A0-000 act1/floor17 Kin Priest,
A0-000 act2/floor16 Knowledge Demon, A5-000 act1/floor17 Vantom. Each has legacy
and typed-Ashwater arms plus independent full-prefix replay: six trials and six
replays. These are known single-battle counterfactuals, not fresh full runs or
resumptions of E165 outcomes. No HP/deck/reward edits; exact original source/DLL
hashes and every prefix command must match.

Budgets:300 actions/120s each trial,120s each replay,600s total, zero model API
calls. Synthetic polarity checks separate from gameplay. Gate: three baseline
original outcomes match; six natural battle terminals and exact replays; no
illegal action, stderr/source/resource mismatch; optional exhaust preserves
positive-valued cards; at least one clear/HP gain and no regression; the two
non-Ashwater controls retain identical transitions. A pass retains only this
opt-in semantic correction, not general potion competence or win-rate evidence.

```
python3 -m unittest discover -s tests -p test_ashwater_semantics.py
python3 scripts/validate_ashwater_e166.py plan --output experiments/E166/plan-v1.json
# commit the frozen plan
python3 scripts/validate_ashwater_e166.py evaluate --plan experiments/E166/plan-v1.json --output artifacts/runs/e166-evaluation-v1.json
```

E165 raw source is ignored `artifacts/runs/e165-evaluation-v1.json`; published
evidence remains on closed PR319 / `codex/e165-live-campaign-transactions`.
Ownership of Gambling Chip and indiscriminate early potion use are separate
defects and are not changed in this experiment.

## Result — local semantic gate passed

Frozen tested SHA `c916e916755837f252f2b67cb67b5ca543e22f8e`.
Two synthetic semantic tests pass: optional exhaust removes a Status while
preserving a Power and a zero-preview attack; generation keeps positive
selection polarity; inconsistent mandatory Ashwater context rejects.

| Known natural entry | Legacy | Typed Ashwater |
|---|---|---|
| A0 Kin Priest | clear,39HP | clear,39HP; identical transitions |
| A0 Knowledge Demon | defeat,0HP | **clear,33HP** |
| A5 Vantom | clear,36HP | clear,36HP; identical transitions |

All three legacy arms exactly reproduce the original E165 boundaries. Six
complete trials and six independent complete-prefix replays match;12 raw bundles
pass hash/stderr checks; all budgets pass,106.157 seconds wall. Full versions,
commands, root/state/DLL/source hashes and every outcome are in
[evaluation-v1.json](evaluation-v1.json). No external model/API use or game edits.

At the identical Ashwater menu (`7597915e...`), legacy exhausts seven positive
cards; typed selection skips optional exhaust. Both arms still use the same
early-potion program. The revised fight plays Vicious on turn1 and Hellraiser on
turn7, then wins on turn11 (61 decisions); legacy loses on turn11 (59 decisions)
without playing either Power. The intervention preserves multiple cards and
changes subsequent draws; do not attribute the entire gain to Hellraiser alone.

Decision: merge PR322 as an **opt-in semantic correction and diagnostic**. Do not
change default FrozenProgram, potion timing, native gameplay or neural policies.
This is one previously observed failing encounter plus two non-trigger controls,
not new seed/generalization evidence. E165 remains one natural defeat and one
ownership interruption; this counterfactual is not a resumed full-run victory.
Opening ownership is tracked separately in E167/#321 and resource usefulness in
E168/#323. Fix those before another expensive fresh hybrid full-run trial.
