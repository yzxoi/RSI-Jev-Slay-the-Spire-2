# E005 native save replay and branch feasibility

Issue6. Hypothesis: a byte-for-byte copy of the player's native room save plus the recorded action prefix can reproduce current combat in isolated CLI processes. Use the game engine rather than expanding ad-hoc arithmetic. Live game/save remains untouched. Ordinary room saves are not arbitrary mid-combat snapshots.

Fixed first input: native Ironclad A0 EFUZ4NHFCXBT floor7, current turn6. Freeze save bytes locally (ignored), hash input, and freeze native trace prefix before probing. Require identical projections of hand order, enemy HP/block/intents, player HP/block/energy/powers and draw/discard where available. Two independent loads and identical action prefixes must match. Measure time. If native projection differs, stop and identify gaps; do not use failed shadow predictions for live decisions. No formal victory claim from replay branches. Next-phase branch tests require a separately committed plan once state parity is established.

Privacy: keep raw native save local; public evidence only sanitized state projections, hashes and commands without user IDs. No write_continue_save/set_player/enter_room/set_draw_order calls; load_save is directed only at the private copy. Budget5 minutes of local probes,0modelcalls. Current real game remains paused at an autonomous boundary during capture; no native commands from this experiment.

Iteration1 c9ac25e loaded the ordinary-profile save twice identically (1.03/0.96s), but it was another older seed and floor17, not the active modded run. This does not meet native parity. The initial capture path was wrong; retain its result and input hash. Iteration2 selects modded/profile1 and checks embedded rng.seed==EFUZ4NHFCXBT before copying. No source save edits.
