# E092 — visible native single-player continuation

Issue [#176](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/176). Resume the sole single-player save currently available on native profile 1 via the legal `continue_run` action. The current menu has `continue_run` and no active autoplay. The loaded run ID, character, ascension and floor must be read and fixed before campaign control; no other run is a substitute.

Hypothesis: the merged native controller can progress this genuine save under the existing `retaliate` policy, with state-bound Astra intervention only at explicit danger/review boundaries. The measurement is deepest reached floor and actual outcome, not an estimate of win rate or a promotion of closed E090/E091 branches. One game trajectory only, no rollback, editing, rerolling or selective restart.

Controller flags: `--execute --combat-policy retaliate --auto-combat-selections --guard-exhaust-selection --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop`. Each same-run segment is limited to 200 actions, 900 seconds and $0.10 Jev budget. Stop at GAME_OVER, an unresolved safety/uncertain-delivery boundary, user pause or an operational budget. At an explicit review boundary, commit a fresh-state-hash-bound single Astra action before executing it. Re-read state after every uncertain delivery; never resend speculatively. The overlay is read-only, translucent and follows this run's trace on the Built-in Display.

All local raw traces remain under ignored `artifacts/runs/`. Record source code commit and command, game/mod/model versions, run ID, ascension, floor/HP progress, actions, Jev usage/cost, every trace hash and any stall/defeat. Publish compact evidence, PR result comment and merge only if the observation and hashes are complete. This run is a field observation, not a paired strategy test.

## Loaded save and provenance before controller execution

The one legal `continue_run` menu action loaded run `8X3876DS2JL4`, single-player Ironclad Ascension 1, floor 11 combat at 45/87 HP. A fresh `wait_until_actionable` read verified a stable player-action state. Game v0.111.0, STS2 MCP mod v0.16.2; `health_check` showed `play_running=false`. The overlay launched successfully on Built-in Display index 0 at opacity 0.78, bound to this run's trace root; its reader code is from local commit `d800be4` because the UI module is not yet in merged main. It has no game-action path.

This native save predates the last E081 trace checkpoint (same run ID, floor 11 turn 6 at 20/87 HP). The game restart restored an earlier floor-11 state. E092 is therefore explicitly a **restart-from-save continuation**, not an uninterrupted extension of E081 and not a rollback-selected win claim. Only the newly loaded state and subsequent E092 actions count for this observation; no alternate branch will be replayed or selected.
