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

First gameplay segment at tested SHA
`5f067c606e25485b1da4f53627ccbeb47d1465c4` used:

```sh
python3 -m rsi.campaign --expected-run-id F1GR9R0YXCCC --combat-policy planned --pause-on-danger --danger-hp 20 --auto-combat-selections --max-actions 80 --max-seconds 300 --max-usd 0.10 --output artifacts/runs/e051-segment01.json --execute
```

Jev chose the +11 max-HP Neow option; the normal native run advanced through
rewards and card choices to floor 5, turn 3, HP82/91. The controller accepted
63 actions with zero action rejections, made 19 Jev requests, and reported
$0.006872166 spent plus $0.004032 conservatively estimated for three model
calls with unknown usage. No Astra decisions were used. The segment stopped
before selecting or sending action 64 because three consecutive Jev requests
failed with `URLError: nodename nor servname provided, or not known`.
There was no uncertain MCP action delivery and no native `GAME_OVER`; this is
a network/controller interruption, not a battle loss or win. Raw trace SHA-256
`fd7dd8115ab2c9cc6264d906616bfbf30f75c9de919b56dd37e62995ec214b40`;
compact metrics are in `segment01-result.json`.

The user requested a pause to improve missing-probability presentation in the
read-only overlay. Read-only MCP state confirms the same run still sits in
floor-5 active COMBAT with `play_card`/`end_turn` legal; the controller process
has exited. Do not resume game actions until the user asks to continue.

The user subsequently authorized resuming the **same** run. Read-only state
confirmed run `F1GR9R0YXCCC`, floor5 turn3 HP82/91 and a ready combat action
gate; OpenRouter DNS resolved again before restarting. Segment 2 at tested
SHA `f8f744b0efc7d42930faac672c7da722ec2d4607` used the same campaign
command as segment 1 with output `artifacts/runs/e051-segment02.json`. It
accepted 80 actions with no rejection, advanced through the floor8 Rest and
floor9 combat to a floor10 CHEST, HP85/91. Jev made 23 requests for
$0.004462332; Astra interventions remained zero. This was an ordinary
`budget_boundary`, not a failure or terminal outcome. Raw trace SHA-256
`228c43208ce3d2a85566ecd7723d019a09c696aadd6b3ada82867a74e7c9a20a`;
compact metrics are in `segment02-result.json`.

Segment 3 at tested SHA `095863f9fb54a14d203ca7e4143c9f2fee2dc0b0`
used the same planned campaign command with output
`artifacts/runs/e051-segment03.json`. It accepted 80 actions, zero rejections,
and stopped at a normal budget boundary on floor16 REST, HP17/91; 28 Jev calls
cost $0.00516453, with no Astra action yet. Raw trace SHA-256
`af5b26f4b86eb86ebfe322c274f65b681e1adca2046fb8abbb2deff7ef3146a3`.
Trace audit identified a major policy failure at floor14 `SLIPPERY_BRIDGE`:
Jev selected “reroll the offered card” nine times, paying escalating HP
3+4+5+6+7+8+9+10+11 = 63, then removed one Strike. The observed event entry
was HP86; it exited at HP23. This is not evidence of any alternate event
outcome. Floor15 combat was won, but battle heal left only HP17. The next
floor16 REST offers Heal27 or Smith. Since HP17/91 is an explicit danger
boundary, bind one Astra choice to Heal index0, raising HP to at most44 before
the Act1 boss; count it as intervention 1. The exact observed state hash and
action are in `rest-heal.json`. Execute once with `rsi.native_step`, inspect
actual HP and only then resume Jev. The event-reroll policy defect is a
separate atomic experiment; do not change the current run's policy silently.

The precommitted Heal at tested SHA
`b97cafaec2a8186049eefdad156a28a5225d3f46` was accepted exactly once:
`python3 -m rsi.native_step --choice experiments/E051/rest-heal.json --expected-run-id F1GR9R0YXCCC --output artifacts/runs/e051-rest-heal.json --execute`.
Native HP rose 17→44/91; REST now offers only Proceed. This is Astra
intervention 1, not an autonomous Jev choice. Raw trace SHA-256
`b3ca9c47687fbecfadc0e2cfd6b1b1c48178b9d4e3ba231495fe26e1667bfa38`;
compact evidence is in `rest-heal-result.json`. The repeated-bridge-reroll
policy defect has its own preregistered issue #97 / E052 and remains unchanged
in this native run.

Boss entry at tested SHA `edfbb0cde5ef5271cca1ea4f8568f74758818d30`
used two controller actions (`REST.proceed`, forced MAP node) with output
`artifacts/runs/e051-boss-entry.json`: floor17 COMBAT, HP44/91, zero Jev
calls/rejections. Trace SHA-256
`b06e372668276429b54ac9390e64f921960ef1ea245e871efea9f0c8d3e47f7c`.
Observed Lagavulin Matriarch HP222, Plating12, Asleep3, Sleep intent; the hand
has Hellraiser, and three potions include Regen, Vulnerable and Strength.
This is a high-impact boss boundary after the severe bridge HP loss. Bind
`boss-room-plan.json` to the exact native state, using Regen Potion as the
opener and compact sleeping/setup guidance for Jev. Count this as Astra
intervention 2. The next controller segment uses `room_guided`, at most 12
actions/120 seconds/$0.03, and `--pause-on-danger --danger-hp 30` to inspect
before another potentially lethal boss exchange. This safety threshold is
intentionally higher than the earlier ordinary-combat threshold 20, and the
result remains a guided, not purely autonomous, run.
