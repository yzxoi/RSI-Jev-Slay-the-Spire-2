# E081 — visible A10 upper-bound run with overlay

Issue: [#154](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/154). Baseline: merged `origin/main` at `8ea843d434a64fedd3247a2dafd6f6092fab8293`; no strategy code change in this experiment.

Hypothesis: the merged native controller can make measurable progress in one fresh, visible single-player Ironclad A10 run while the read-only decision overlay follows its trace on the Built-in Display. The target is the natural final result, not an estimated win rate.

Fixed input: fresh natural game seed, Ironclad, Ascension 10 if the selector permits it. Controller flags: `--combat-policy retaliate --auto-combat-selections --guard-exhaust-selection --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop`. Bounded segments: 200 accepted actions, 900 seconds, $0.10 Jev spend each. Resume on the same run only after checking fresh state. Astra may supply state-bound single-action choices for explicit review boundaries. Overlay: `--opacity 0.78 --screen 1`; it only reads the local trace. No edited HP, rewards, RNG or victory flags, and no rollback.

Decision rule: stop at natural GAME_OVER/victory or an unresolved unsafe/uncertain action. Report all segments including failures and stalls, maximum floor and Boss progress, action count, model usage and trace SHA-256 hashes. This single run is exploratory. A new strategic modification requires a separate atomic issue and experiment.
