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

Implementation/plan-generation SHA `b41e4aa`: six focused ownership/resource/context checks passed. All four seeds, two arms, runtime and every rsi source hash frozen before gameplay.

## Frozen evaluation finished; supplementary audit planned

The registered v1 failed completeness: three Astra runs stopped at the shared 200-packet budget and one failed at Pael's Tooth (8568 legal combinations >4096). All four controls naturally lost in act one; all four treatments reached act two. This is a positive first-act observation, not a completed full-run comparison; no promotion or budget extension. Do not change v1 outcomes or continue its games.

A separate **read-only post-hoc** audit will replay the four recorded treatment prefixes with no new decisions (120seconds each), tabulate request overhead, and describe the A5-000 act2 floor11 Obscura fight. Exact prefix replay only verifies executed transitions; it cannot satisfy the original eight-terminal gate or produce a new victory sample. `scripts/audit_campaign_e160.py` is committed before this verification. This adds no policy, training, seed or game-state edit.

## v1 result and disposition

Tested gameplay SHA `e99d72bb918d70b705267280a9e2a5708207e4b9`; frozen source hashes remained unchanged. Teacher commits bind 200 packets from `c2650fd` through `e4a4805`. See `evaluation-v1.json`, `audit-v1.json`, and the [D024 report](../../docs/research/learning-search/2026-10-04-hybrid-campaign.md).

| Case | Control | Astra | Cleared fights control/Astra | Expert packets |
|---|---|---|---|---|
| A0-000 | defeat Act1 floor12 | packet cap Act2 floor12,80HP | 5/11 | 56 |
| A0-001 | defeat Act1 floor17 | packet cap Act2 floor7,60HP | 7/11 | 56 |
| A5-000 | defeat Act1 floor15 | packet cap Act2 floor11,16HP | 7/13 | 57 |
| A5-001 | defeat Act1 floor17 | selection error Act2 floor1,100HP | 6/9 | 31 |

First-act passage0/4→4/4 is an exploratory observation. Zero full victories observed; all treatment outcomes are incomplete, so no full-run win-rate estimate or formal paired progress promotion. This cautious macro baseline is weak, and treatment cases share expert context/cross-case discoveries. No final330acceptance seeds used.

Registered evaluation:1826.106wall seconds,62.377aggregate CPU seconds;200requests,2,165,658input characters,105,144output characters. Actual expert tokens/USD unknown. The generic manifest's zero model API usage does not measure Codex/Astra task inference. Combined waits6392.277seconds sum concurrent runs, not wall time. Shared cap causes scheduler-dependent truncation and should be replaced by fair independent run budgets in a new protocol.

Raw audit12bundles passed;1656actions and200committed expert packets passed fresh legal/ownership/binding checks. Four control terminal replays matched. Supplementary audit SHA `5e7e2a43b4fad6238caa1f4e62511ded77f115f9`: all four treatment recorded-prefix replays matched every wire command,4more bundles passed,36.575seconds. This does not repair the eight-terminal gate. No HP/reward/state edits, seed replacement, resumed run or native gameplay.

```sh
python3 scripts/audit_campaign_e160.py --source experiments/E160/evaluation-v1.json --output artifacts/runs/e160-audit-v1.json
```

Request phases: map48,card_reward46,shop26,potion_reward22,event21,card_select19,rest18;7maps had a sole route plus resource alternative. Obscura diagnostic:83HP→10HP before BurningBlood→16HP;15turns;30targeted card plays at reviving minion vs11at leader;Juggernaut+ playable turns3/5/7/13,never played. This is observational, no alternative outcome proven. Expert evaluation also overestimated Gorget's durability: Plating decays each turn.

Decision: merge opt-in harness, complete positive/negative evidence and research records only. Do not promote a default policy or continue this per-button recipe. Follow-up atomic proposals #310–#313 are registered, not executed; address subset representation, acquire-and-reserve handoff, macro call compression and encounter objectives. Evidence supports further hybrid engineering, not a cheap/stable full-run claim.
