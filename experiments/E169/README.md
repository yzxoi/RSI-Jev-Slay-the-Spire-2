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
