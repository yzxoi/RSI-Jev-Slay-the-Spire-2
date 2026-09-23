# E054 — Second fresh native Ironclad A0 run

Issue #100. Hypothesis: with the merged E052 bridge guard, the existing
`planned` controller and Jev macro choices can produce a genuine native A0
victory with fewer than 40 state-bound Astra actions. E051 is the practical
comparison: the previous uninterrupted Ironclad A0 run lost on floor27 after
404 native actions, 140 Jev calls and 20 Astra actions. Different random
seeds mean later progress cannot by itself establish a causal policy gain.

Fixed starting situation: native profile1 at E051 `GAME_OVER` intro,
`F1GR9R0YXCCC`. Continue the old game-over screens to the main menu as
recorded setup actions; then select single-player Ironclad A0 and embark on
the next normally generated seed **exactly once**. Record its run ID. No
seed reroll, rollback, game-value edit, or second game writer. The controller
uses merged E052 SHA `2d43577d8223d505388af7fdd445efa423f54c61`.
The read-only native overlay may follow the new trace automatically.

Policy: `rsi.campaign --combat-policy planned`, Jev macro decisions,
automatic combat selections, and danger pause at HP≤20 before spending
combat energy. Segment caps: 80 accepted actions, 300 seconds and $0.10
Jev; whole-run caps: 1500 accepted actions and $1 Jev. Astra may bind at
most 40 state-specific actions at explicit danger/compatibility boundaries.
Every intervention and resume is recorded. Stop at genuine terminal,
unresolved uncertain delivery, game interruption, or stated budget.

Success requires native `GAME_OVER.is_victory=true`, not a battle reward or
floor milestone. Report final floor, HP, bosses, actions, Jev calls/cost,
Astra decisions, all stalls/losses, exact tested SHAs, commands, actual
game/mod/model versions and trace hashes. Raw MCP/model records remain local
under ignored `artifacts/runs/`; compact sanitized results go in this
directory. If Slippery Bridge appears, report real guarded choices and HP
separately. One run is exploratory, not a measured win rate. Publish PR
comments and merge/close by observed evidence.

Before the new run, bind one terminal-screen continuation action to the
observed E051 game-over fingerprint. This is setup, not a rollback or an
E054 in-run decision. Re-read the next screen before further action.

Old-game-over continuation at tested SHA `0551905` was accepted once. The
native E051 screen moved from intro to `summary_ready`; its save status is
now **verified**. Trace SHA-256
`9a20e3a19e958e44ae9b76080395d52171ad4af87bfee6bdf006dcba0a6ccd75`.
This post-terminal UI step does not change E051's floor27 defeat. Bind
`return_to_main_menu` from the verified summary as the next setup action.
