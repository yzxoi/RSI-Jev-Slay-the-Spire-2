# E113 — Bounded multi-seed decision-maker selection

Status: completed; no decision-maker promoted. The protocol below was preregistered before fixture generation or model calls. Date: 2026-09-29.

## Question and hypothesis

Does a cheap reasoning model (`deepseek/deepseek-v4.1-flash`, low reasoning) outperform Jev (`typesafe/jev-1.13`) enough on unseen engine continuations to justify replacing its direct-action role? A zero-API current-hand search is the practical baseline. A model gets no permanent role merely because it is cheap. This is a decision-maker audition, not a full-run win-rate claim or an Astra distillation test.

## Fixed inputs and common information

- Seeds `e113_audition_20260929_001` through `_006`; all five characters; ascension 10. Seeds 001–002 are a compatibility cohort (10 cases); 003–006 are a locked confirmation cohort (20 cases). No prompt/policy tuning on either cohort in this iteration.
- Generate natural prefixes using existing retaliation/trigger-aware beam search (width 40, depth 8), existing deterministic macro policy, explicit free potion claiming, and no manual potion use. No game values/RNG/rewards edited. Record all 30 sources, including deaths and stalls.
- For each source, stop on entering floor 10, leaving Act 1, death, 500 actions or 90 seconds. Freeze the **latest first-turn combat entry before that boundary**, plus the latest card-reward entry strictly preceding it if available. Selection happens once, before any model sees a fixture. This tests mid-Act-1 states reachable by this baseline, not a representative distribution of the entire game. If the baseline dies early, retain its last entry and report the early death.
- Exact action prefixes and full-state hashes must replay identically for every arm. Frozen fixtures are committed before model evaluation. Use the preserved v0.111.0 CLI DLL (original SHA `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`), not current Steam. Explicit potion mode enabled. CLI automatically claims gold/relics.
- Same legal candidates, full relevant observation, generic STRATEGY, six recent actions and limited numeric incoming-damage information for both models. One fresh action per observation. Jev keeps its typed choice API; DeepSeek uses a strict choice-ID JSON schema, temperature 0, low reasoning, max 4096 completion tokens, reasoning text excluded. Neither gets teacher examples or seed-specific plans. API envelope differences are part of this practical backend comparison.

## Arms and outcomes

1. `program`: existing `choose_plan(..., triggers=True, retaliation=True)` and `fixed_macro`; freely claims potions, reserves manual potions. This baseline has known approximate-mechanics and macro weaknesses, disclosed rather than hidden.
2. `jev`: current direct typed-choice policy, including legal potion actions.
3. `deepseek`: specified cheap reasoning model with identical choice space/information.

Combat: continue each frozen battle to actual combat exit or defeat, with card/potion selections controlled by that arm. Record win/loss, final HP, enemy HP, turns, potions used, actions, legality/errors, API tokens/cost, API latency and wall time. Ending at a selection inside combat is not a victory. A win outranks a loss; equal wins compare final HP, a difference of <3 HP is a tie. Errors/budget exits are failures and remain in denominators, separately labeled.

Reward: each arm chooses **one** card reward (including skip), then the same deterministic program continues until two new battles finish, defeat, or the floor-10/Act-1 boundary. Record survival, battles completed, final HP, resources, chosen card/skip and full trace. This is a limited-horizon downstream utility check, not a globally correct card-ranking label. No teacher-agreement metric. Shops, upgrades, Act-2/3 bosses and native multiplayer are outside this initial selection gate.

## Budget and exit conditions (frozen before testing)

- At most 30 combat + 30 reward continuations per arm (180 total); no repeat sampling to hunt a favorable outcome. Four concurrent engines maximum. Single backend request timeout 45 seconds (Jev existing timeout 25), no model retry or fallback in this experiment.
- Shared backend limits: Jev 1000 requests / $1; DeepSeek 1000 requests / $4; total $5. DeepSeek provider price ceilings $0.50/M input and $1.50/M output; conservative byte-count input reservation plus maximum output reservation. Unknown billing stops that backend. All failures billed/reported when known. Maximum elapsed model evaluation 60 minutes; individual battle 240 actions / 900 seconds, reward continuation 300 actions / 180 seconds. Unstarted cells are explicitly budget-censored.
- Before confirmation: halt a backend for 3 consecutive request failures or >10% failed/invalid requests once >=20 requests have completed. Continue healthy comparators; no substitution. >10% fixture replay/engine errors makes the strength verdict inconclusive and stops promotion. Operational failures are not counted as gameplay defeats.
- **Combat promotion** on the 20 locked cells requires >=19 valid completed cells, no fewer battle wins than program, >=6 paired improvements and <=2 regressions against program, plus median signed final-HP gain >=3 (defeats use actual remaining player HP). To replace Jev directly, DeepSeek must also have no fewer wins, >=6 improvements and <=2 regressions against Jev. These are screening thresholds, not a statistical population-win-rate proof.
- **Speed/cost gate:** p95 model response <=15 seconds and mean reported API cost <=$0.05/completed combat. A quality winner failing speed remains a candidate for sparse high-impact routing only. Missing billing prevents cost promotion.
- **Reward role** independently requires >=19 comparable locked cells, >=6 better and <=2 worse outcomes versus program (survival, then completed battles, then HP with 3-HP tie band). No reward improvement means no claim to that role.
- If neither model clears a role, stop direct-action prompt polishing for that role; keep program fallback and open a separate representation/planning experiment if justified. Do not silently extend seeds, budget, prompts or thresholds. No live controller default is changed by this screening experiment.

## Reproduction and evidence

Implementation SHA, commands, fixture/source attrition, exact dependency/model/provider IDs, per-cell results, paired decisions, trace hashes and limitations will be appended after each committed iteration. Raw requests/responses/state transitions stay under ignored `artifacts/runs/`. Public files contain compact results and hashes, no credentials or game binaries.

Official interface references checked 2026-09-29: [model](https://openrouter.ai/deepseek/deepseek-v4.1-flash), [reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), [structured output](https://openrouter.ai/docs/guides/features/structured-outputs). The public model-list API currently advertises $0.30/M input and $1.20/M output; UI headline rates differ, so actual response `usage.cost` is authoritative.

## Iteration 1: fixture generation

Issue: [#216](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/216); PR: [#217](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/217).

Generator code SHA `efcc033`. Command: `python3 -m scripts.evaluate_deciders_e113 freeze` (stdout `artifacts/runs/e113-freeze.log`). Six adapter/budget/boundary unit tests passed using `python3 -m unittest discover -s tests -p test_decider_backend.py -v`; the initial dotted-module invocation was incompatible with this repository's non-package tests directory and was corrected before evaluation.

All 30 source configurations completed without engine errors or time limits: 7 reached the floor-10 boundary and 23 died earlier. All have a replayable combat entry and preceding card reward. Entry HP ranges 1–76. This is deliberately a stress-oriented distribution: the last reachable combat often exposes the source policy's failure. It must not be interpreted as random-battle or full-run win rate. Exact source results and hashes are in `freeze-result.json`; common commands/states are in `fixtures.json`. No LLM saw these fixtures during generation. Interface metadata is frozen in `model-metadata.json`.

## Iteration 1: model evaluation result

Tested code/fixture SHA **`fc286e0`**, command `python3 -m scripts.evaluate_deciders_e113 evaluate` (stdout `artifacts/runs/e113-evaluate.log`). Elapsed 413.853 seconds. All 180 preregistered cells have records, including censored cells; **180 records does not mean 180 completed continuations**. Program and Jev completed all 120 of their combat/reward continuations. DeepSeek completed six reward continuations, eight cells failed to return complete model output, two started cells were censored after the backend gate (one battle and one reward before its API request), and 44 cells never started after the stop. The final trace audit corrected an initial provisional count of one started / 45 unstarted censored cells.

| Locked confirmation cohort (seeds 003–006, 20 cells per task) | Program | Jev | DeepSeek |
| --- | --- | --- | --- |
| Combat wins | 4/20 | 1/20 | Not evaluated after pilot stop |
| Combat better / worse / tied versus program | — | 0 / 4 / 16 | Unavailable |
| Reward downstream survival at fixed boundary | 4/20 | 4/20 | Not evaluated after pilot stop |
| Reward better / worse / tied versus program | — | 2 / 2 / 16 | Unavailable |

Across pilot + confirmation, program won 7/30 battles and Jev 2/30. Jev's confirmation combat p50/p95 request latency was 0.7085/1.014 seconds, and cost was $0.042975072 for 20 battles. It meets the speed/cost gates but fails the combat and reward quality gates. All 416 Jev API requests were legal/complete; API schema reliability did not translate into good play.

DeepSeek stopped at 20 completed requests, eight of which had `finish_reason=length`; one already-in-flight request subsequently completed, for **21 total / 8 failures**, $0.044993645. It completed no combat episode, so **no DeepSeek battle-win-rate comparison is available**. Its output and token budgets were not increased after failures. Seven length failures were on AtlasCloud with all 4096 completion tokens reported as reasoning; one was on Together with non-JSON analysis in content and zero separately reported reasoning tokens. Provider assignments were not randomized matched comparisons; this does not prove a different provider fixes the model. Requests used low reasoning, not reasoning disabled.

Total reported provider cost: **$0.121056779** (Jev $0.076063134; DeepSeek $0.044993645). All billing was known; no retry, fallback model or manual Astra gameplay intervention was used. This excludes Astra's development/review cost, which is not metered by this runner.

### Protocol deviation: network timeout was not a hard deadline

The 45-second `urlopen` timeout bounded socket inactivity, not total response duration. Three DeepSeek requests exceeded 45 seconds (59.941, 73.385, 87.982 seconds). Actual durations remain in the trace and results. All 21 responses have known cost; the reliability exit still fired and no new calls began after it. This flaw invalidates any claim that the request deadline was enforced, and is an additional reason not to promote the backend. It does not alter the program/Jev paired outcomes. A hard-deadline transport correction will be committed and tested locally; the paid model experiment will **not** be rerun or silently relabeled with that later code SHA.

Decision: reject Jev's unrestricted direct-action role under this representation; do not promote its reward role. Reject the tested DeepSeek/OpenRouter configuration operationally, with strategy strength **inconclusive**. Keep live defaults unchanged. Stop prompt polishing or repeated sampling within E113. A future experiment must change a named factor (such as verified turn-plan selection instead of raw actions, or a separately validated reasoning/provider budget) and use new confirmation seeds.

## Iteration 2: hard deadline correction and evidence audit (no new model calls)

Reason: the measured keepalive behavior defeats a socket-inactivity timeout. The new transport isolates each HTTP request in a killable subprocess and bounds total elapsed time; credentials use stdin pipes, never command arguments/logs. A total timeout leaves billing unknown and stops that backend. The regression test uses a local server continuously sending whitespace, plus a successful JSON response test. This is transport validation, not a new gameplay trial. Iteration 1 results remain bound to `fc286e0`; no earlier failed attempts are removed.

The audit checks complete cell coverage, raw trace/wire/stderr hashes, tested SHA, exact entry replay, ledger reconciliation and frozen selection gates. End-turn observations are diagnostic flags, not assumed regret labels.

Validation at `d3d0dec`: six decision/budget/boundary tests and two HTTP tests passed. The latter demonstrates that continuous keepalive bytes cannot extend a total timeout. No additional provider calls were made. Commands:

```sh
python3 -m unittest discover -s tests -p test_decider_backend.py -v
python3 -m unittest discover -s tests -p test_http_deadline.py -v
python3 -m scripts.audit_deciders_e113
```

The audit reconciled 416 Jev requests ($0.076063134) and 21 DeepSeek requests ($0.044993645), with known billing and no missing responses. It verified 136 executed continuation traces and 136 matching replay entries; the other 44 preregistered cells were unstarted after the backend exit. Overall DeepSeek request p50/p95 was 34.625/73.385 seconds. The 30 source traces are also checked by the final audit.

Jev ended turns with positive energy and at least one playable card in **118/142** observed end turns; program did so in **13/153**. These flags are not all automatically mistakes (saving a card or avoiding retaliation can be correct). A concrete trace example, `001-defect`, round 1: after Defend, two 1-cost Strikes remained with 2 energy; two 5-damage-attacking Slimes had 10 and 8 HP and no powers/block. Two Strikes could kill one, but Jev ended the turn. The corresponding program battle won at 42 HP; Jev died. That whole-battle difference cannot be attributed solely to this one action without an additional counterfactual.

All-six-seed battle results by character (program / Jev wins out of six): Ironclad 1/0, Silent 2/0, Defect 1/0, Regent 2/0, Necrobinder 1/2. The Necrobinder exception cautions against declaring Jev universally useless; the locked cohort still contains no paired improvement for Jev.

### Scope of the decision

This rejects **unrestricted raw-action Jev with this observation/candidate representation**, not every possible Jev subtask or the existing guarded hybrid controller. It rejects **DeepSeek low reasoning + 4096 completion tokens + current automatic provider routing** as a deployable fast direct-action backend; it does not establish DeepSeek's strategic ceiling. Raise-output-budget or provider-specific experiments would be different configurations and need new preregistration. Rewards used the same imperfect downstream program and a short horizon, so global deck-building ability remains unresolved.

The next useful architectural test is to make the program own legal execution and numerical evaluation, expose several computed turn plans, and ask a model for a low-frequency plan/goal decision. This changes the model's job rather than adding more prose to the same failing raw-action prompt. Before DeepSeek gameplay retesting, demonstrate bounded reliable structured output under a fixed provider/budget configuration. Use new confirmation seeds; E113's observed seeds are now development data.

PR disposition: **close without merging**. Neither backend passed its frozen promotion conditions. Keep all code, fixture/result commits, raw local traces and public hashes on this branch; no live default changed. The hard-deadline correction is tested experimental tooling, not a claim of a successful new model evaluation.

Final audit code SHA: `13634f8`; `python3 -m scripts.audit_deciders_e113` passed with 30 source traces, 136 continuation traces and 136 entry replays verified, zero integrity failures. Compact evidence is in `audit.json`; individual cells and all censored configurations remain in `results.json`.
