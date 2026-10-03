# E159 — First action versus continuation controller

Issue [#306](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/306). Preregistered after E149; no training/default changes.

## Frozen hypothesis and protocol v1

E149's complete pilot improved only4/15TRAIN seeds;18/30roots had all discovery paths lose. Hypothesis: weak student continuation masks recoverable first-action value. A controller comparison can test that explanation but cannot establish that remaining failures are unavoidable.

Use all30E149 bank-v1 roots,15Ironclad TRAIN seeds at A0/A5/A10 (five each), the exact E158 runtime/save certificate and original game RNG. Freeze all120factorial cells before execution: forced first action {original actor, E149 selected}, crossed with continuation {frozen E140 BC1702 greedy, frozen existing program}. No new candidates, search, random streams, state edits, seed replacement or API calls. Only six roots have different first actions; duplicated cells remain in the full accounting, not independent evidence. This is a reused TRAIN-state diagnosis, not an unseen-seed win-rate experiment.

Program: `complete_baseline` with unchanged `CONTROL={mode:legacy,loss_price:1.5,potions:early}` for combat and selection interruptions; `cautious_macro` for campaign decisions. The latter claims available potion rewards, uses existing cautious map/healing rules, takes the first ordinary reward and leaves shops. It is a practical reproducible control, not an optimal teacher. Preserve the triggering card/potion across card-selection chains; in-battle event-generated card rewards route to the selection evaluator and are not battle clears. Action legality is checked against the fresh complete menu. Source file hashes/settings/checkpoint/runtime and first-action identities are frozen in plan-v1.json. The actor's previous-action context remains exactly E149's.

Play all paths to actual game-over; record the first real encounter's outcome/resources separately and do not overwrite it when later defeated. Initial rewards cannot be labelled a clear. Utility: defeat−1; genuine first clear1+.25HP/maxHP. Record HP/potions/gold/deck hash, first-fight transition hash, full transition hash, Act2/Act3 and victories. All60actor-continuation full paths AND their first-fight prefixes must reproduce E149 exactly. Independently replay six program paths: actor first action, index000 combat/preparation at each difficulty. Replays reproduce full actions and first-fight observations; no replay resampling.

Budget600s wall/1200s aggregate parent+childCPU,4workers,90s/2400actions per full suffix; six replays included. Rotate the four arm execution orders by root index modulo4, retain all caps/errors/unstarted cells. In-flight CPU may overshoot; that fails the gate. All original source and certificate hashes checked; errors are never converted to losses. Known unsupported Trial#294/CrystalSphere#64 remain explicit failures.

Primary contrast: program minus actor continuation with the SAME original actor first action. Average the two roots within each of15game seeds; bootstrap those seeds10000times,RNG159. Report all four cells, the first-action×continuation interaction, mode/difficulty strata and per-root outcomes. Passing requires all120paths/60paritychecks/6replays complete and exact, raw audit and budgets; mean first-fight utility gain>=.10, lower95%cluster bound>0, at least3positive seeds, no negative mode/difficulty mean, and no actor Act2/victory lost when changing continuation under either first action. This only authorizes a separately registered stronger-teacher test. It does not unlock E150, change weights or establish full-run strength. Failure stops this recipe; two weak controllers failing is not an impossibility proof. Final330acceptance seeds unused.

## Reproduction

```sh
python3 -m unittest discover -s tests -p test_continuation.py
python3 -m unittest discover -s tests -p test_root_teacher.py
python3 -m unittest discover -s tests -p test_map_prefix.py
# Commit implementation before plan; copy and commit plan before any game path.
python3 scripts/pilot_continuation_e159.py plan --output artifacts/runs/e159-plan-v1.json
python3 scripts/pilot_continuation_e159.py evaluate --plan experiments/E159/plan-v1.json --output artifacts/runs/e159-evaluation-v1.json
```

Each output is immutable. Raw state/decisions/expected replay plans stay ignored under artifacts/runs; public compact records contain outcomes and hashes. Historical game v0.111.0, local M3 Max CPU; actual dependencies and runtime hashes recorded by each manifest.
