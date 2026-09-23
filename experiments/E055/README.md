# E055 — retained Beckon self-loss

Issue: [#102](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/102). Hypothesis: the current native lethal-end-turn predicate and Toxic-only reservation omit `BECKON`'s direct `HpLoss` on retained cards. A narrow candidate constraint that reads the card's structured ID and dynamic value can prevent demonstrated lethal energy spending without pretending to simulate future draws or unknown mechanics.

Baseline: `origin/main` at `2d43577`, with `--combat-policy room_guided`; existing `reserve_toxic_energy` and `end_turn_will_kill_player` behavior. Fixed retrospective inputs: **every 57 Soul Fysh floor-17 `before` combat decision states** in E054 run `DCEND0WRAPGL`, across four SHA-pinned native traces listed in `scripts/freeze_beckon.py`. Character Ironclad, ascension 0, native game v0.111.0, mod v0.15.0, Jev `typesafe/jev-1.13-20260917`. The tracked gzip fixture retains only player, hand, enemies, relics, native predicate and offered candidates. Generate it with:

```sh
python3 scripts/freeze_beckon.py --source-root /Users/yzxoi/RSI-Jev-Slay-the-Spire-2-e054/artifacts/runs --output experiments/E055/frozen-soul-fysh.json.gz
```

Decision rule: promote if the fixed terminal-risk state is flagged before the final energy is spent, the legal Beckon survival option remains, nonlethal controls are preserved, and tests cover zero/multiple Beckons, energy shortage, sufficient Block, lethal attack without Beckon, and plausible immediate kill. Count changed candidate sets over all 57 states. A changed offline action set is **not** a counterfactual battle outcome or win. Budget: no new native run in this issue; one fixed-state replay plus synthetic mechanic tests. Any full-run strength claim requires a separately preregistered fresh game.

The raw native traces remain local under ignored `artifacts/runs/`; this fixture is a compact, sanitized decision-state projection. Implementation, exact tested SHA, commands, results and decision will be appended as committed iterations.
