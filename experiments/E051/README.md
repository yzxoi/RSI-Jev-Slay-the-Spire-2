# E051 — Fresh native A0 run with sparse Astra intervention

Issue #95. Hypothesis: the merged planner and Jev policy can finish a fresh,
uninterrupted Ironclad A0 run with substantially fewer Astra decisions than
the heavily guided E048 victory. E048 is the practical comparison, but its
application hang and save rollback mean it is not an uninterrupted control.
One attempt cannot estimate win rate or high-ascension strength.

Fixed input: native profile 1 at `MAIN_MENU`, single player, Ironclad,
ascension 0, and the next normally generated seed exactly once. Record the
generated run ID at embark. No reroll, save rollback, edit to HP/rewards/win
flags, or second game writer. The overlay is read-only and follows the same
ignored raw trace directory.

Policy: `rsi.campaign --combat-policy planned` for autonomous combat and Jev
macro decisions. Use segments capped at 80 accepted actions, 300 seconds and
$0.10 Jev each; whole-run caps are 1500 accepted actions and $1 Jev. Astra
may supply at most 30 state-bound choices after an explicit danger, requested
review or compatibility boundary. Every intervention and resume is recorded.
Stop at genuine terminal, unresolved uncertain delivery, game interruption or
the stated budget. Do not silently restart a failed run.

Success requires a normal native `GAME_OVER is_victory=true` and verified
summary/save without rollback. Record the final floor, HP, bosses, actions,
Jev calls/cost and Astra interventions even on loss or stall. A later floor is
only progress; a single success is not a measured win-rate improvement.
Keep raw MCP/model records under ignored `artifacts/runs/` and publish compact
sanitized summaries with SHA-256 trace hashes. Commit implementation/setup
before execution and results afterward, then comment evidence and merge/close
reason on the PR.

Environment expected from the last verified run: game v0.111.0,
STS2-Agent v0.15.0 and model `typesafe/jev-1.13-20260917`. The trace manifests
will capture actual versions, code SHA and per-segment commands.
