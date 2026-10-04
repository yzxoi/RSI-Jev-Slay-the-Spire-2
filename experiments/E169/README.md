# E169 — Typed opening subset search

Issue #326. Test whether changing only Gambling Chip's opening discard set produces better verified continuations. Baseline is FrozenProgram/E159, including legacy early potions and all later selection behavior. Do not combine E166/E168 changes: this question varies one initial action. State restoration replays the certified historical engine's exact natural command prefix without changing HP, cards, RNG or rewards.

## Fixed protocol

Five registered roots: control run21526f07-71b7-47c0-912c-14217e63bc89 at commands124/148/172/196, treatment runcd9a5cb9-82d9-430e-ba29-05debd6f7974 at306. All derive from **one game seed under two macro policies**. Four baseline boundaries come from E165's original control; the interrupted fifth uses E167's independently verified diagnostic defeat. Original E165 stays interrupted. plan-v1.json freezes wire/trace references, every entry hash, explicit discard/redraw effect, prior action, 32 legal subsets, three fixed comparison choices and original end hashes.

The explicit domain is limited to these registered Gambling Chip openings. The CLI does not export selection-effect identity; evidence is room-entry command, relic, optional bounds and historical lifecycle. Reject mismatched contexts/mandatory selections/>32 subsets rather than silently using a generic remove-card heuristic. This is not a production detector for every relic combination.

160 candidate continuations, four workers, <=300 actions/120s per trial, <=900s total. Every command in every restored prefix must match. All candidates, errors and timeouts retained. Rank real clear before defeat, then living HP, then retained potion count; dead inventory has no utility. Stable ties prefer fewer discards then lexicographic card indices. Comparison includes unchanged baseline, keep all, and a fixed discard-only-Status/Curse rule. These simple comparators are members of the same frozen bank, not extra tuned trials.

After selecting from the completed bank, persist choices, independently replay baseline and selected paths (10 engine runs), and freshly execute the selected first action with autonomous frozen continuation (5 runs). All175 bundles must pass; all five legacy baselines match their source endings. Local headroom gate needs at least one strictly better verified continuation, no lost baseline clear, complete candidate coverage and budget/fidelity. No new-seed, full-run, default promotion or cheap real-time deployment claim. Search includes a known deterministic future and is explicitly an oracle diagnostic; timings include restoration.

No network model/API calls. Runtime v0.111.0 and dependency/code hashes recorded in manifest. Synthetic tests cover domain/budget rejection and terminal ranking, not game performance. If no verified local gain appears, stop this expansion. A gain requires a separately registered generic selector/new-seed evaluation before deployment; do not teach a lookup table of these five answers.

```sh
python3 -m unittest discover -s tests -p test_opening_subset.py
python3 scripts/search_opening_e169.py plan --output experiments/E169/plan-v1.json
# commit fixed plan
python3 scripts/search_opening_e169.py evaluate --plan experiments/E169/plan-v1.json --output artifacts/runs/e169-evaluation-v1.json
```

Implementation, frozen plan and results are separate commits. Failed attempts remain in history.

## v1 result and decision

Tested `fdb5898` (implementation `b267685`). Both synthetic tests passed. All160 candidates completed (no cap/error/illegal action); all five baselines match their source endings,10 independent baseline/selected replays match, and all five freshly executed selected continuations match the searched transitions. All175 bundles pass. Wall321.098s, zero model/API calls. Integrity and local-headroom gates pass.

| Root | Legacy baseline | Keep all / Status-Curse only | Exhaustive selected | Clear subsets |
|---|---|---|---|---|
| control act1 floor12, Nibbits | clear22HP | clear28HP / clear28HP | clear42HP; discard Strike0, Defend1 | 32/32 |
| control act1 floor14, Inklets | clear40HP | clear22HP / clear22HP | clear42HP; discard Fight Me!3 | 32/32 |
| control act1 floor15, Jaxfruit/Flyconid | clear18HP | clear18HP / clear18HP | clear30HP; discard indices0,1,2,3 | 32/32 |
| control act1 floor17, Vantom | defeat | defeat / defeat | defeat; keep all on tied rank | 0/32 |
| treatment act2 floor11, Entomancer | defeat | defeat / defeat | clear36HP; discard Rupture3 | 18/32 |

Four roots improve, one ties; clears3/5→4/5 are correlated diagnostic counts, not a win-rate estimate. The simple fixed rules cannot rescue the target Elite and lose18HP versus baseline at floor14; do not replace the default with keep-all/status-only. The selected Rupture discard is state-specific evidence, not a generic instruction to discard Rupture. Vantom's32 failures only bound opening choice under this frozen continuation; they do not prove the encounter/deck impossible under other play.

Aggregate restoration consumes92.037% of candidate elapsed time. Per root the32 rollout elapsed sums are161.66/184.51/201.26/230.44/336.97s; these are summed trial times, not measured standalone four-worker latency. Search also affects subsequent draw order, so improved outcomes are causal effects of the opening action as a whole, not isolated per-card value estimates. Do not add HP gains across roots as if they were one improved natural run.

Decision: merge the opt-in diagnostic/domain utilities and evidence; default live/battle policy remains unchanged. A separately registered unseen-seed generic bounded solver is justified. E169 itself does not evaluate a learned model, new seeds, a full run, an inexpensive deployed solver or native Steam execution. Raw traces remain under artifacts/runs with published hashes; all iterations remain committed.
