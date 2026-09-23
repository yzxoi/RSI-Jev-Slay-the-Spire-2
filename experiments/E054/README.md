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

Return-to-menu at tested SHA `3971fd7` was accepted: native screen is
`MAIN_MENU`, profile1, singleplayer session. Trace SHA-256
`13c6ad4f2a7dc900891bdb1acec6e40ce1f060b13aab2a3ddd0d1c50fdaca227`.
Bind `open_character_select` as the next setup action. The menu fingerprint
matches E051's earlier main menu because no run is active; no saved game is
being loaded.

Character selection at tested SHA `0f74844` confirmed singleplayer,
Ironclad selected, A0, one player, no specified seed, and Embark legal.
Trace SHA-256
`ab9c59c0a5a2973e3160401378a46369290a85ae4e8512c701dceae083b5a083`.
Bind exactly one `embark` action to create the next normal random run.

Embark at tested SHA `9bb46f9` was accepted once and generated run ID
`DCEND0WRAPGL`: floor1 NEOW, Ironclad A0, 80 HP. The exact action command
was `python3 -m rsi.native_step --choice experiments/E054/embark.json
--expected-run-id run_unknown --output artifacts/runs/e054-embark.json
--execute`. Trace SHA-256
`b97a108d8fff371ec44a439b20066f219ee30bb97ec59597a472a243e0ed1cb3`.
Native game v0.111.0 and STS2-Agent v0.15.0. The Neow offer is one potion
slot plus two random potions, two extra Act1 boss relics, or two random Neow
relics with a random curse. Jev will choose; no Astra action has been used in
the new run. The first segment uses the predeclared `planned` policy and
HP≤20 danger pause, 80-action/300-second/$0.10 limits.

Segment 1 at tested SHA `83803529573f89497ef7caf3160aed5cd764d89a`
used:

```sh
python3 -m rsi.campaign --expected-run-id DCEND0WRAPGL --combat-policy planned --pause-on-danger --danger-hp 20 --auto-combat-selections --max-actions 80 --max-seconds 300 --max-usd 0.10 --output artifacts/runs/e054-segment01.json --execute
```

Jev selected the Neow offer for two additional Act1 boss relics. The run
defeated floors2–4 and reached floor5 COMBAT at HP49/80; 80 accepted actions,
15 Jev calls costing $0.002534868, zero Astra decisions. One `play_card`
request was explicitly rejected while the native action gate transiently
advertised only save-and-quit; the controller refreshed state and did not
retry an uncertain delivery. The boundary is ordinary action budget, not
loss or victory. Raw trace SHA-256
`1ea3bd95604d1c2e186314ebfc220b9d2020481574bc28e65c6aaa830ad075e6`.
Read-only native state subsequently confirmed the same floor5 fight ready
at HP49, one DAMP_CULTIST enemy with 17 HP and Attack26 intent. Continue
the unchanged `planned` policy in segment2 under the same caps.

Segment 2 at tested SHA `beeb014d89102302157e70e1bc86b1f22277d26e`
used the same command with output `artifacts/runs/e054-segment02.json`. It
accepted 80 actions, zero rejections, made 19 Jev calls for $0.003721074,
and defeated floors5–9. Jev healed at floor8 REST (34→58 HP). Segment ended
on floor9 REWARD at HP43/80; this is an action budget boundary, not a run
outcome. No Astra action was used. Raw trace SHA-256
`25c10eb48318283cf5637fd747fee11d897dd5059eb9e4b030c6f64498ad943a`.
Continue unchanged policy in segment3 with the same fixed caps.

Segment 3 at tested SHA `7beac44b9b4781728eff4f5f7775ec977e472180`
accepted 80 actions, zero rejections, and used 20 Jev calls/$0.004377618.
It cleared floors11 and13, healed at floor12 and floor16, and reached the
Act1 Soul Fysh boss on floor17 at HP45/80, turn7. Raw trace SHA-256
`2966da8f067f440aece5c11497090ca30732a243409773f25d66a43d1fbd76c7`.
Floor14 was `THIS_OR_THAT`, costing 6 HP; `SLIPPERY_BRIDGE` did not occur,
so the E052 guard has no native outcome here. The boss has 104 HP and
displayed Attack24, while player is Vulnerable2 with Radiant Tincture and
Speed Potion. Bind `soul-fysh-room-plan.json` to the fresh state as Astra
intervention 1: use Radiant Tincture first, then provide compact defensive
guidance to Jev. Because this is a boss with imminent damage, raise the
danger pause from 20 to 25 HP for this **bounded room segment only**; cap
at 20 actions, 120 seconds and $0.03 Jev. The room plan stops at MAP after
boss rewards or an earlier review. This is a distinct guided segment, not
an unchanged-policy autonomous result.

Soul Fysh room segment at tested SHA `ab97f4e` accepted 14 actions, zero
rejections, 13 Jev calls/$0.003645474. The Radiant Tincture opener counted
as Astra intervention 1. Boss104→47 HP; player45→22 HP and the scoped
≤25 danger pause fired at turn10. Trace SHA-256
`e1287eeec501b94e31b579fba9c63dd981630d164d24f5d89b0a9a8129d5531e`.
Current boss has Intangible1, Attack13 plus Debuff; player HP22, energy4,
with two Beckon cards that each cost 6 HP if retained at turn end. Bind
`soul-fysh-beckon-plan.json` as Astra intervention 2, using Speed Potion
index1 before Defend/Beckon management. The next room segment uses
`room_guided` with 20-action/120-second/$0.03 caps and HP≤20 review so
the current 22-HP turn can proceed; the lethal-end-turn guard remains. This
is an explicit scoped threshold change from 25, not the earlier policy's
unchanged result.

Beckon defense room at tested SHA
`60ed1b97edc7230358e6a1b43dcdb499183e324e` accepted 7 actions,
zero rejections, five Jev calls/$0.001359918. Speed Potion was Astra
intervention 2; Jev played Defend, both Beckons, Pommel Strike and Battle
Trance before ending the turn. HP22→13, boss47→46 under Intangible; the
≤20 review fired at turn11. Trace SHA-256
`6cbff3a547f394679c20e18087c9fdd24840b4e23a9f3784c97bbbe388ba3fd9`.
Soul Fysh now has no Intangible and uses StatusCard2, no attack. The hand
has Twin Strike and three free Angers at player HP13. Bind a fresh
`soul-fysh-burst-plan.json` opening Twin Strike as Astra intervention 3,
then let Jev use the free attacks and react to subsequent native intents.
This bounded room segment lowers the pause threshold from 20 to 12 so the
current HP13 turn can execute; the separate lethal-end-turn guard remains.
Cap at 20 actions, 120 seconds and $0.03 Jev. This is a scoped guided
variant, not an unchanged-policy autonomous outcome.

Soul Fysh burst at tested SHA
`316f93c1295cb4e0c64727909a16e13e32c85777` accepted 10 actions,
zero rejections, seven Jev calls/$0.001923264. Twin Strike was Astra
intervention 3; Jev then played three free Angers. The boss survived at
18 HP into turn12. Jev played Shrug, Taunt and Strike, leaving 13 HP,
14 Block, zero energy, one Beckon in hand and enemy Attack24. Native
`end_turn_will_kill_player=false` despite the card's displayed 6 HP
end-turn loss. The selected end turn produced native `GAME_OVER`,
`is_victory=false`, floor17, HP0. Raw trace SHA-256
`ce6a3e17f58a808ecda925690f0b725a4201d8f139fe2efadf1d1ddcca740a15`.
The 10 untracked raw trace files, including four setup actions, all passed
SHA-256 recheck. After the observed terminal the game process and MCP
endpoint stopped; save was still pending at the last native state, so no
save verification is claimed. Issue #102/E055 separately preregisters a
delayed Beckon-loss guard. The alternative of using the last energy on
Beckon rather than Strike is a counterfactual, not a played result.

The uninterrupted E054 run ended normally after 271 in-run native actions,
79 Jev calls costing $0.017562216, and three Astra room-opening actions.
One explicit transient `play_card` rejection occurred in segment1, with no
uncertain action delivery. Compact totals and exact final code SHA are in
`terminal-result.json`. The hypothesis of a genuine A0 finish failed.
Compared with E051, this different-seed run stopped earlier, at floor17;
the E052 bridge guard was not exercised because the corresponding event
did not appear. Do not promote a win-rate or E052 native-strength claim
from this outcome. Close this negative experiment PR after publishing the
result; retain the branch and raw trace hashes for subsequent diagnosis.
