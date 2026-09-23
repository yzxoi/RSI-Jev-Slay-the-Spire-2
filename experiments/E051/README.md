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

Setup at tested SHAs `e47cd53` and `d8f090d`: the precommitted menu action
opened character selection, where the native state confirmed Ironclad,
singleplayer, ascension 0, and no seed. The precommitted Embark action was
accepted once and generated run ID `F1GR9R0YXCCC` at the floor-1 Neow event.
No rejected actions or restarts. Commands:

```sh
python3 -m rsi.native_step --choice experiments/E051/menu-open.json --expected-run-id run_unknown --output artifacts/runs/e051-menu-open.json --execute
python3 -m rsi.native_step --choice experiments/E051/embark.json --expected-run-id run_unknown --output artifacts/runs/e051-embark.json --execute
```

The exact raw trace hashes and compact setup outcomes are in
`setup-result.json`. The observed Neow offered starter removal, +11 max HP,
or Greed plus 333 gold. The first campaign segment will leave this choice to
Jev to measure the autonomous policy, using `planned`, `--pause-on-danger
--danger-hp 20`, and the preregistered per-segment caps.
