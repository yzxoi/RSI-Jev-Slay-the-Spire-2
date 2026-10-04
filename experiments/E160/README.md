# E160 — Astra campaign planning with fixed program battle execution

Issue [#308](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/308). User redirected the main goal to strong affordable hybrid play on2026-10-04. Pure-network acceptance is a separate research line.

## Protocol v1, before any game attempt

Four NEW Ironclad DEV seed strings: `e160_campaign_Ironclad_A0_000`, `e160_campaign_Ironclad_A0_001`, `e160_campaign_Ironclad_A5_000`, `e160_campaign_Ironclad_A5_001`. Every seed has program_campaign and astra_campaign, eight natural start_run→game_over attempts. Fixed original runtime v0.111.0 with E158adapter hashes. No seed replacement, rollback, state edits, trial rescue or policy changes while running.

Baseline uses E159 FrozenProgram with its existing cautious campaign rule. Both arms use that SAME legacy trigger/retaliation combat algorithm, early available potions, and context-preserving battle selections. No Jev, neural weights, extra MCTS or Astra battle decisions in this isolation. Astra treatment owns all nontrivial campaign actions (route, rewards/skip, shop/removal, event, rest/upgrade and their selection menus). Potion-generated in-battle rewards and selections remain program-owned. A sole legal action is mechanical in either arm.

Astra may set typed current potion-ID reservations until Elite/Boss, released if HP/maxHP is below an explicitly chosen threshold in[0,.5]. Rules apply to all copies with that ID, are replaced by the next expert packet, and mask ONLY the combat proposal's available-potion view; no engine inventory/value is mutated. Every action is revalidated against the real menu. This resource policy is part of the campaign treatment; the potion schedule is not claimed unchanged. Macro choices may legally use or replace potions. No tactical action sequences or hidden escalation.

Both arms read get_map at actual maps. Keep a persistent <=1200character campaign summary; refresh deck/relic/map text when their hashes change, preserve full raw states. Every expert request binds case/run/sequence/state, fresh candidates, prior summary and resources. A one-action packet is committed before use and its immutable SHA is in the trace. Treatment author may inspect its current/past trajectory, but not contemporary baseline results until all expert decisions end. Independent games have one writer each. Initial manifest pins code; subsequent commits contain only teacher decisions, not code changes.

Budgets:2400actions,120compute seconds excluding teacher wait per run;90packets/run;200packets total;600seconds/request;5400seconds global wall;1200aggregateCPU seconds. Four Astra runs and four controls launch concurrently, control results withheld from console. Eight independent full wire/action replays after expert decisions freeze, inside aggregate budgets. Errors/caps/unfinished are not deaths. All fixed cases reported. Known Trial#294 and CrystalSphere#64 compatibility gaps remain failures if encountered.

Integrity requires8normalterminal attempts,8exact independent replays, legal fresh committed expert actions, zero teacher combat ownership, frozen program source hashes, raw audit and budgets. Exploratory progress tuple per pair is lexicographic `(full_victory, completed_acts, genuine_battles_cleared)`; all components reported separately. Complete acts counted only at living next-act maps (or final victory); initial/generated rewards never count a fight clear. Development continuation gate requires no lost baseline victory, >=2/4positive pairs, positive mean pair sign and nonnegative mean pair sign within each difficulty. This small pilot does not establish stable win rate. Passing permits a separately registered larger/newseed hybrid test, not default promotion. Failure retains evidence and stops this recipe.

Current Codex/Astra task supplies expert decisions; no automated billed expert API. Record packet count, JSON character volumes (NOT tokens), waits, computation and source hashes. Actual Astra tokens/USD unknown. Final330network acceptance seeds untouched; this pilot is a separate hybrid track.

## Reproduction

```sh
python3 -m unittest discover -s tests -p test_campaign_teacher.py
python3 -m unittest discover -s tests -p test_continuation.py
python3 scripts/pilot_campaign_e160.py plan --output artifacts/runs/e160-plan-v1.json
# Commit the copied plan before launching any games.
python3 scripts/pilot_campaign_e160.py evaluate --plan experiments/E160/plan-v1.json --output artifacts/runs/e160-evaluation-v1.json
# Author answers from ONLY pending treatment requests, then commit before consumption.
python3 scripts/reply_campaign_e160.py /tmp/e160-answers.json
```

Raw full requests/states/wire remain in ignored artifacts/runs; public teacher response packets contain concise choices/plans/reservations, bound to immutable source hashes. Replaying those recorded packets is regression verification, not new Astra reasoning or an independent win sample. Do not reuse output paths or overwrite a prior teacher response.
