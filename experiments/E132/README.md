# E132 — Reusable elite battle-entry saves

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/248

Status: preregistered; no game evaluation yet.

## Question and hypothesis

Can real map-boundary saves provide reusable elite-battle starts across difficulty levels, avoiding replay from the beginning for every training/search rollout? E121 already showed faithful map saves (median 3.234 -> 1.117 s restoration) and E124 used them in search. E128 did not build snapshots for its new bank and unnecessarily retained full-prefix replay. This experiment reuses that infrastructure; it does not claim arbitrary mid-combat memory snapshots.

## Fixed inputs and budget

Ironclad, ascensions 0/5/10, seeds `e132_20261002_a` and `e132_20261002_b` at each ascension: six prespecified configs. Historical official v0.111.0 and unchanged pinned adapter/DLLs. The existing resource-aware E120 preparation policy legally advances toward the first elite; preserve every death, unavailable entry, error and cap, without replacing seeds or editing game values. A Boss entry is not substituted for an elite. Max 90 s / 700 actions per preparation, two workers, no live-game control or paid-model calls.

Freeze the complete entry bank before save/path evaluation. For each available Elite entry, A reconstructs the canonical prefix; B repeats it, saves at the actual preceding Map boundary, and enters; C loads that unedited save in a new process and enters. Require exact map and battle hashes and the save's original ascension. Each path 20 s.

Capture two reference trajectories per entry with full-prefix restoration: the unchanged control and an epsilon=0.15 legal-action rollout (RNG derived from case + fixed label), at most 30 s / 120 actions. Independently reconstruct each complete battle plan with the existing continuation verifier and extend through rewards to the next battle's second-turn opening or legitimate death (30 s / 80 extension actions). Freeze these complete action/hash paths before reuse. Incomplete source paths remain reported and do not become valid references.

Verify each frozen path with B (fresh prefix plus a save call) and C1/C2/C3 (three independent fresh-process loads of the same save). Check every before/after state, including generated selections, terminal outcome, rewards and next-turn draws. This covers divergent legal policies from the same start; neither trajectory is a new independent seed. Once all available-case fidelity checks pass, measure three paired fresh A/C restorations per available entry, alternating order by case-index + repeat. Do not exclude slow samples. No warm-process reset or engine changes in E132 (E129 stays separate).

## Decision rule

Bank completeness requires all six prespecified entries available; bank fidelity requires every A/B/C and all continuation/reward/draw comparisons exact, unchanged files and zero execution/cap/audit errors. Report preparation availability separately from conditional fidelity. A useful pilot speed result requires pooled paired median restoration speedup >=1.5 and C p95 no worse than A p95, with all comparisons retained. This is a new scoped research gate, not a relabeling of E121's stricter failed speed gates or a production default promotion.

Use a 10-minute batch work budget excluding implementation/analysis; stop launching new evaluation work if exhausted, retaining unstarted cases. Preserve local unedited save files, raw traces, public hashes, code SHAs, timing and all failures. No policy-training, search-strength, full-run win or hidden-state-universality claim. If valid, publish a reusable index for these exact entries/engine versions and a documented reset/rollout API; do not silently plug an uncertified snapshot into E128 or mutate ascension inside a save.

## Iteration 1 — natural bank freeze

Preparation used clean SHA `63c45db` with the pinned v0.111.0 engine. All six fixed configurations reached genuine Elite entries; no seed replacement or state editing. The freeze batch took 16.563 s; all six raw bundles passed the hash audit. Eight existing checkpoint/restore unit tests passed. The first unittest invocation used package-style names even though `tests` is not a package; it failed discovery before any gameplay, then discovery mode passed.

```sh
python3 -m unittest discover -s tests -p 'test_checkpoints.py'
python3 -m unittest discover -s tests -p 'test_research_restore.py'
python3 scripts/validate_elite_bank_e132.py freeze --output experiments/E132/fixtures-v1.json
```

The bank is frozen before capture; failures in the next stages remain evidence.
