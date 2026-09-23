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

Segment 4 at tested SHA `f45926ef3eb7565efd2fa64284e1c48a2a3f4c9b`
ran `room_guided` with `boss-room-plan.json` for 12 accepted actions, zero
rejections, 13 Jev calls/$0.0032025; raw trace SHA-256
`3dcb12b30c33cd3b55aa140173cc34c49613df45cca661aa67ceb12817bb6d4e`.
The bound Regen Potion opener executed, Hellraiser was played during sleep,
and native boss HP fell 222→115 while player HP ended at 43/91. At the next
observed turn the boss intends Attack12 plus Defend, player has zero Block and
3 energy, with Shrug It Off 8 Block/draw1 plus Defend 5 Block in hand. Strength
Potion remains. Bind `boss-strength-plan.json` to this exact state as Astra
intervention 3: use Strength Potion, then ask Jev to cover the shown attack
before spending spare energy. Evaluate a short 10-action segment with danger
threshold 30; do not attribute its outcome to unguided play.

Segment 5 at tested SHA `ee85e319dfc6890d69f548ca879777ac25ebeb8c`
used `room_guided` with `boss-strength-plan.json` for 10 accepted actions,
zero rejections, 11 Jev calls/$0.002674014; raw trace SHA-256
`3ff07ed8bedebc1a5f0c3f4e666f84554cd5d8d9032e2710b8e8a222cb8e1be5`.
The Strength Potion opener executed; Jev covered the shown attack and cut
boss HP115→32 while player stayed HP44/91. Current turn7 has zero energy,
Block10 versus displayed Attack21, only unplayable cards in hand and one
Vulnerable Potion. The next segment returns to the ordinary `planned` policy,
at most 20 actions/180 seconds/$0.05 with danger threshold30. This tests
whether Jev can finish the low-HP boss without another Astra action; reassess
only if a real danger or terminal boundary appears.

Segment 6 at tested SHA `9e53d79a781f7196a24a732eb189f4328abd8f3a`
used the ordinary planned controller for 20 accepted actions, zero
rejections, 11 Jev calls/$0.00290766; raw trace SHA-256
`01e99f5041412d471e0afca498347dd075bbc0b2fc3c074069be77c99e57b87c`.
The player took the displayed 21 attack through 10 Block (HP44→33), then
Jev killed Lagavulin Matriarch and reached the native reward screen. Normal
act transition healed the player, and the controller handled a floor18 event
and card selection before stopping at floor19 COMBAT, HP90/91, `act_id=1`.
This is a genuine Act1 boss win, not a complete-run victory. Astra count
remains 3. Resume with the ordinary planned controller and 80-action/300 s/
$0.10 caps, danger threshold20 outside a boss.

Segment 7 at tested SHA `4581753c83168434b68c74d956e1d8e160f5da4f`
ran the ordinary planned policy for 72 accepted actions, zero rejections,
20 Jev calls/$0.00499632. Native floor23 combat reached HP3/91 and stopped
with `expert_required: low_hp_before_spending_energy` before another action.
Raw trace SHA-256
`1dfca1032b44c11f091216923f988965f945f59c7d49f4dfe8efa9480938c9e6`.
Observed current turn7: Silk Bowlbug21 HP has Debuff intent, Slumbering
Beetle78 HP attacks22; player has zero Block, 3 energy, two Strikes, Pommel
Strike, Barricade+ and Battle Trance. Attack Potion can give a free attack;
Radiant Tincture grants energy. Re-read after the turn-settle transition
showed `play_card` and `use_potion` legal. At 3 HP, a 22 attack is lethal
unless blocked, mitigated or the beetle is killed. Bind a single Astra
rescue action, Radiant Tincture at potion index1, to increase available
energy without spending a card play; inspect its exact effect before choosing
cards. This is intervention 4, and no counterfactual survival is claimed.

The state-bound Radiant Tincture at tested SHA
`f14238d704797a5ad506b31a1b0c80cbff969bb7` was accepted once with
`python3 -m rsi.native_step --choice experiments/E051/rescue-tincture.json --expected-run-id F1GR9R0YXCCC --output artifacts/runs/e051-rescue-tincture.json --execute`.
Native energy rose 3→4, HP stayed 3; trace SHA-256
`1ccd6fb832334726e1ee17c2e8d4d0013a37af123e788c8c66763db26bc229a5`.
The active attacker remains Beetle78 HP with Attack22. Because Battle Trance
would prevent later Pommel Strike draw, bind Pommel Strike at current hand
index2 targeting Beetle index1 as the next Astra action; inspect the actual
draw before any subsequent action. This is intervention 5, not an assertion
that a survivable line exists. Exact state/action: `rescue-pommel.json`.

Pommel Strike at tested SHA `5ea593548ebb60289bee174ce912592aca3ba918`
was accepted against the attacker: Beetle78→68 HP, player HP3, energy4→3,
and the drawn card was Flame Barrier (12 Block for 2 energy). Trace SHA-256
`5c3ef273ad6d6df64608def9f2f883229c132afb3d07c0460635eaa186e64418`.
Flame Barrier alone leaves 10 unblocked from Attack22 and is lethal at HP3.
Battle Trance remains playable at hand index3 for 0 energy and draws three;
bind it next, then evaluate actual block/kill possibilities. This is
intervention 6. Do not spend energy on Barricade or blind Strikes first.

Battle Trance at tested SHA `6f12246e36522c6de96d6550a47d62830f5678cc`
drew Iron Wave, Dismantle and Eternal Armor; HP3, energy3, Beetle68 HP.
Trace SHA-256
`86dca83b7fb0895204cf0a756178bdd806fb4c9977d262fbe2f531e5fd4506a1`.
Flame Barrier12 plus Iron Wave5 is only 17 Block versus Attack22, lethal at
HP3; Eternal Armor costs all 3 energy and does not provide enough immediate
Block on its own. The only remaining flexible resource is Attack Potion index0,
which offers one of three random free attacks. Bind its use as intervention 7
to inspect real choices for Weak, extra Block or a kill. Opening an offer is
not a survival result; do not guess the card before the native selection.

Attack Potion at tested SHA `f527e278b51ba3582a1ae916f5bfa2ada61b4d26`
opened native selection of Molten Fist, Thunderclap and Conflagration; raw
trace SHA-256
`2ddacc0f2e258fddfaf0f65b0686fa462237ff58bba47ae00e99e4c511054d6a`.
None grants direct Block or Weak. Thunderclap's free all-enemy hit applies
Vulnerable1, which activates the existing Cruelty+ 50% damage bonus and makes
Dismantle hit the Beetle twice. This is the only offered path with a plausible
same-turn kill using three remaining energy, though exact native damage is
not yet established. Bind `rescue-thunderclap-select.json` to option1 as
intervention 8, then inspect its actual temporary card/index before playing.

Thunderclap selection at tested SHA
`89661ef9369aceaec9e4ef6b42e219e17372187b` was accepted: the potion
placed a 0-energy Thunderclap at current hand index7. Trace SHA-256
`b510fb89a8a1a23a9e68cb23b1f9cb862f57f6b48eab2f42686b72e8ba4f3add`.
Both enemies still have their pre-attack HP and the Beetle still intends22;
selection alone dealt no damage. Bind the actual free Thunderclap play at
index7 as intervention 9 and re-read both enemy HP/status after it resolves.

Thunderclap at tested SHA `a39982b540a2b9ffe7d3ef41fa37a22f3721812b`
dealt exactly 5 to each enemy and applied Vulnerable1: Silk16 HP,
Beetle63 HP, player HP3/energy3. Trace SHA-256
`6c34c56daa81ef9655114565933699071ef822cbe860b37c8e9459041253d1ec`.
The active attacker still intends22. Dismantle at current hand index5 will
strike the Vulnerable Beetle twice; this is the best observed chance to
remove the attacking source within the remaining energy. Bind target index1,
inspect actual damage, then decide whether two Strikes or another line can
finish it. This is intervention 10; the kill is not presumed.

Dismantle at tested SHA `a90318c73b6d003cb5972cf0de8109109a618936`
dealt 36 actual damage (two hits under Vulnerable/Cruelty), Beetle63→27 HP,
player HP3, energy2; raw trace SHA-256
`d88ce443e1764359e32e4832039a92d41093c29fdc2f4958e456a825c1385150`.
Two Strikes remain at hand indexes0 and1, each displaying7 base damage
before target Vulnerable and Cruelty. Two strengthened hits may remove the
attacking Beetle before it deals22; bind the first Strike index0 target1 and
measure its actual damage. This is intervention 11, not yet a guaranteed kill.

First Strike at tested SHA `52d7120e8c2fab8afcb66dcc136da41f2802519b`
dealt 14 actual damage, Beetle27→13 HP, player HP3, energy1; trace SHA-256
`ec5de32f553966cf0705193272427eca987dcdf27af3ab5c97c98c03dc038d59`.
The remaining Strike is now hand index0, target Beetle index1. The observed
14 damage exceeds its 13 HP, so bind that second Strike as intervention 12
and verify the Beetle's death. The nonattacking Silk enemy will remain; do
not conflate killing the attacker with winning the whole battle.

Second Strike at tested SHA `f5650c289d1e5bb83859a65e4b731742b3fd9f7b`
killed the 13 HP Beetle before its 22 damage attack. Player remains at 3 HP,
energy0; only Silk16 HP with Debuff intent remains. Native action accepted;
raw trace SHA-256
`14981a7bfe3f2217695b6dc92ea6473696e1fe7c105cd3540de57db4caa50e1a`.
The result demonstrates survival of the immediate lethal attack, not battle
victory. Bind end turn as intervention 13 because no energy remains, native
state reports the end turn nonlethal, and the surviving enemy has a Debuff
intent. Inspect the next hand and intent before further play.

End turn at tested SHA `a9d3543` advanced to turn8 without HP loss;
Silk16 HP now attacks 4×2, player HP3, energy4, and hand includes Shrug It
Off at index3. Trace SHA-256
`bbede2bdf7cc1c0a4ef0633530ca962a7d60e2bee27a16302126a8490f41d1a5`.
Bind Shrug It Off as intervention 14: its 8 Block covers the shown attack,
and the draw may expose a way to kill Silk this turn. Re-read after draw.

Shrug It Off at tested SHA `3fd8460` granted 8 Block and drew Defend;
Silk remains at 16 HP with 8 incoming, player HP3, energy3. Trace SHA-256
`1b3026841cd7f79b105e4b690c40319f852dd275d0d4f8e953da288dfc94b9d6`.
The only available attack is Strike at hand index2. Bind it to Silk index0
as intervention 15, measure actual damage, then end turn if no other attack
appears. Current Block already covers the telegraphed attack.
