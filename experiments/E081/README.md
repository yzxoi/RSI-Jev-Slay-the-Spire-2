# E081 — visible A10 upper-bound run with overlay

Issue: [#154](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/154). Baseline: merged `origin/main` at `8ea843d434a64fedd3247a2dafd6f6092fab8293`; no strategy code change in this experiment.

Hypothesis: the merged native controller can make measurable progress in one fresh, visible single-player Ironclad A10 run while the read-only decision overlay follows its trace on the Built-in Display. The target is the natural final result, not an estimated win rate.

Fixed input: fresh natural game seed, Ironclad, Ascension 10 if the selector permits it. Controller flags: `--combat-policy retaliate --auto-combat-selections --guard-exhaust-selection --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop`. Bounded segments: 200 accepted actions, 900 seconds, $0.10 Jev spend each. Resume on the same run only after checking fresh state. Astra may supply state-bound single-action choices for explicit review boundaries. Overlay: `--opacity 0.78 --screen 1`; it only reads the local trace. No edited HP, rewards, RNG or victory flags, and no rollback.

Decision rule: stop at natural GAME_OVER/victory or an unresolved unsafe/uncertain action. Report all segments including failures and stalls, maximum floor and Boss progress, action count, model usage and trace SHA-256 hashes. This single run is exploratory. A new strategic modification requires a separate atomic issue and experiment.

Before embark, native profile 1 exposed `max_ascension=1` for Ironclad. The preregistered A10 target is unavailable on this untouched profile, so the actual fixed test is **Ironclad A1**, the highest legal selector setting. `increase_ascension` was accepted once; the selector now shows Ascension 1. This is an input limitation, not an A10 result.

## Native segment 1

The first `--screen 1` overlay launch exited before creating a window because this macOS session listed only screen 0 (`Built-in Retina Display`). Relaunch with `--screen 0 --opacity 0.78 --game-run-id 8X3876DS2JL4` succeeded; a live screenshot showed its semi-transparent, click-through panel over the game's upper right. This is a display-index compatibility adjustment, not a game policy change.

The natural A1 run embarked as game run `8X3876DS2JL4` with Ironclad at 80/80 HP. Controller command: `python3 -m rsi.campaign --expected-run-id 8X3876DS2JL4 --max-actions 200 --max-seconds 900 --max-usd 0.10 --output artifacts/runs/e081-segment01.json --execute --combat-policy retaliate --auto-combat-selections --guard-exhaust-selection --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop`. Tested SHA `7c8a69d37700abb094c8cd6c3d18be05ca63743a`, game v0.111.0, mod v0.16.1, model `typesafe/jev-1.13`. The segment accepted 156 actions through floor 11 at 45/87 HP, including rewards, cards, a shop and a rest. It made 36 Jev calls at provider-reported $0.0073269, with zero action rejections and zero unknown model usage.

The segment stopped with an MCP `wait_until_actionable` timeout immediately after an accepted `end_turn`; it was not a game defeat. The raw trace SHA-256 was verified and is in [segment01-summary.json](segment01-summary.json). A fresh read showed the **same run** on floor 11 turn 3, `snapshot_stable=true`, `can_use_combat_actions=true`, with no controller running. The previous end-turn had therefore completed; segment 2 will resume from this new state without resending it.

## Native segment 2 and Astra boundary

Tested SHA `1af7d179a1973ca26593ef3dcaa718bbdba8fea9`, same command with `--output artifacts/runs/e081-segment02.json`. Starting from verified floor-11 turn 3, the controller accepted Pommel Strike, Dismantle+, Defend and end turn. Its post-action wait again returned the same internal timeout, so the segment stopped after 4 accepted actions at 31/87 HP; fresh read showed **same run**, turn 4, ready. No action rejection or uncertain delivery. [segment02-summary.json](segment02-summary.json) contains the verified raw trace hash. This repeated execution-compatibility failure is tracked separately in [E082](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/156).

E082's first attempted native segment reached an explicit danger-review boundary before any action: 31 HP, 25 advertised incoming damage, 0 block, 3 energy, and four live enemies. Astra's fresh-state-bound opening in [floor11-turn4-fire-choice.json](floor11-turn4-fire-choice.json) uses the available Fire Potion on the 20-HP enemy advertising 9 damage. The potion should remove an attacker and preserve energy for the two Armaments and Defends in hand; that effect is a prediction until the native result is observed. Continue only if the exact state fingerprint still matches. No rollback or game-value edit.

At the next same-run turn-5 review (31/87 HP, 16 advertised attack, three enemies, only Strikes and Defends in hand), Astra precommitted [floor11-turn5-colorless-choice.json](floor11-turn5-colorless-choice.json): use the available Colorless Potion and inspect its three generated choices. This is an on-policy resource choice to avoid an otherwise weak 10-block/6-damage turn; its benefit is uncertain until the native options and outcome are observed.

The Colorless Potion single action was accepted at tested controller SHA `674a8bbb77b012cb13186f0d0ddd33678b856b60`; raw trace SHA-256 `7e11bae2e7a2dac7ca11b8a3649340b2cc72fb278703ec44c3c2cad69eeadbc1`. It opened a three-card choice: Prolong, Restlessness and Shockwave. Astra precommitted [floor11-turn5-shockwave-choice.json](floor11-turn5-shockwave-choice.json), choosing Shockwave because this potion makes it free this turn and it applies 3 Weak plus 3 Vulnerable to all three enemies. The actual play and damage reduction remain to be observed.
