# E101 — exact-engine certification of immediate leader lethal

Issue #193. Preregistered 2026-09-26 before testing.

Refinement of the proposal: a damage preview nominates a move; **it never certifies a win**. Support only legal Ironclad/Silent basic Strikes against the sole non-Minion leader in a Boss room. Require exported single-hit damage >= HP + block. Then start a separate pinned CLI process, replay only the actual accepted start/action prefix, verify the complete current state hash, play exactly that candidate, and require an actual `boss_clear` boundary with positive player HP. Runtime tests at most one nomination per decision; failed/ambiguous/unsupported replay abstains. Before canonical execution recheck candidate legality; canonical after-state must exactly match the proof. Unknown death, retaliation or conditional effects are not guessed away: a numeric nomination cannot pass without real engine terminal confirmation. Other card types abstain. This is CLI-only; not a native safety claim.

Mechanics: `inputs.json` freezes **every before-state from all six E099 traces**, not just the successful witness. Inspect each state; probe every nominated basic Strike. Report state coverage, abstentions, nominations, nonterminal/failed branches and certified outcomes. Offline branch wins are not new first-pass battle wins. Synthetic unit cases for unsupported cards, block, multiple leaders and opaque revive effects are not formal battle outcomes.

Only after exact recovery of witness hash `5d88f1ad36aec0c5a98003bdcf00ecb467d7463661818211827ca406c35251be` and no replay errors: run 12 first-pass continuations, two E099 entries x three repeats x baseline/lethal. Baseline is E099 static-plan Jev **without potion contracts**. Treatment changes only the certified-lethal override; all ordinary card/potion choices and guidance unchanged. No cache, fresh requests, order repeat 0..2 / Ironclad then Silent / baseline first on even repeats and treatment first on odd. <=240 actions and model attempts, $0.20 and 900s per run, shared $1. All failures/exhaustions included, no extra rescue.

Decision: zero false canonical certificates, correct witness recovery and all trace audits required. Compare clears and intervention counts with contemporary baseline. A strength gain is a development signal; no production/generalization claim on repeated historical entries. Even if strength unchanged, a validated opt-in computation tool may merge with the negative evidence. Same old v0.111.0 game hashes as E099/E100; manifests pin exact SHA/dependencies/model output.

Commands:
```
python3 -m unittest discover -s tests
python3 -m scripts.evaluate_lethal_e101 --stage mechanics --source-root /path/to/e099/worktree
python3 -m scripts.evaluate_lethal_e101 --stage battles
```

Raw branches and canonical traces live separately under ignored artifacts/runs. Exact-entry proof time is a real CPU/latency cost and will be reported; it is not free because it uses no LLM.

## Results

Tested code **f967713**, with E100 potion execution disabled throughout this experiment. 142 unit tests passed before execution. [Mechanic branch report](mechanics.json), [canonical results](result.json), [audit](audit.json) preserve all attempts.

Mechanics: 149 frozen before-states; 146 abstentions, 3 nominated states / 4 candidate moves. All four exact replays matched their entry and produced an actual Boss-clear boundary; zero errors/nonterminal nominations in this narrow corpus. Both Strikes at the original missed-lethal witness were verified. Total four-probe elapsed time 24.388 s. These are offline branches, not four extra battle wins or broad effect coverage.

| Arm | Ironclad | Silent | Clears | Jev calls / USD |
| --- | --- | --- | --- | --- |
| Static-plan contemporary baseline | 1/3 (HP 14/0/0) | 0/3 | 1/6 | 154 / $0.035496846 |
| Add certified one-action lethal | 3/3 (HP 22/38/27) | 0/3 | 3/6 | 146 / $0.033626460 |

All 12 canonical runs completed normally. Three runtime certificates were used, each matching the canonical after-state and Boss-clear result exactly. Verification overhead was 5.342–7.279 s per triggered action (18.126 s total). No potion contracts/program potion uses; Jev could still choose potions itself. Aggregate 300 model requests / **$0.069123306**, zero unknown attempts. Returned model `typesafe/jev-1.13-20260917`; exact code/game/patch/SDK hashes retained per manifest. One baseline win here versus zero in E100 illustrates why a contemporary baseline and retained model variation matter.

All canonical/probe hashes, accepted prefix and state chains, legality, terminal boundaries, usage and proof-to-canonical parity pass. Two extra paired clears, no lost baseline clear. The tool cannot save a game that never reaches one of its supported Strike-lethal states; Silent remains 0/3 in this isolated arm.

Decision: merge opt-in verified-lethal primitive and evidence; allow combined E102 testing. No general win-rate or complete-run promotion. Only two related development Boss entries, three sampled repeats, two basic Strike types; unsupported cards abstain. Replay is measured computation, not a free or native-compatible oracle.

Iteration ledger: `f967713` freezes implementation, all-state corpus and both stages before execution. Mechanics gate passed before 12 fresh continuations. E100 results/audit were merged afterward to reuse the generic read-only auditor; no E101 gameplay was rerun or relabeled. Exact reproduction commands above; `python3 -m scripts.audit_boss_trials --experiment E101` reconciles all raw traces. Raw source is the E101 worktree's ignored artifacts/runs.
