# E149 — Independently verified repeated-rollout teacher

Issue [#280](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/280). No gradients or default-policy changes.

## Protocol v1, frozen before collection

Hypothesis: mean outcomes of repeated exact-engine continuations can select root actions that improve the frozen BC1702 actor on independent continuation streams. Start with the uniform selector itself; defer adaptive allocation until this simplest teacher works. This narrows the original three-arm proposal following the roadmap comment: a uniform teacher need not beat itself to qualify. No claim about sequential-halving/Gumbel is possible here.

Collect 15 new natural Ironclad full runs: A0/A5/A10 × indices000..004, seed `e149_train_Ironclad_A{a}_{i:03}`. All phases use frozen E140 BC1702 greedily, unchanged encoder and complete legal menus. For each source choose its last naturally entered battle and the preceding clear reward boundary (Neow if there was no earlier battle): 30 TRAIN roots, paired within15 independent game seeds. This intentionally diagnoses student-visited late difficulties, not representative win rate. Preserve every selected seed, failure and missing root; no replacement. Collection must complete and independent replays of index000 at each difficulty must match before any search. Freeze roots, exact legal candidate lists, root/prefix hashes and checkpoint identity in a tracked bank before search.

At most4 root candidates: actor greedy; legal simple planner/cautious macro choice; end_turn or skip_card_reward when present; remaining slots by descending actor probability, stable legal-order ties. All candidate probabilities and omitted actions recorded. No state/RNG/reward edits. Continuation policy is the same frozen actor sampled at temperature1. At continuation step t>0 use inverse-CDF sampling with a common preselected uniform stream across candidates; force only the first action. Discovery streams `14900000 + root_index*100 + k`, k0..3. Select highest **mean** local utility, ties prefer actor. Local outcome is next genuine battle clear (1+.25HP/maxHP) or death(-1); initial reward is not a win, final reward is not claimed as useful. Potions/gold/deck changes reported separately; this utility is not whole-run value.

Per root budget: <=16 discovery continuations,6 independent validation streams for each of selected and actor (12),2 greedy local continuations,2 greedy full suffixes = <=32 paths. Validation streams `14910000 + root_index*100 + k`, k0..5, disjoint from discovery. Greedy suffixes continue to actual full-run termination and report Act2/Act3 arrival; they are restored conditional evaluations, not independent natural victories. First root of each mode/difficulty additionally has one independent action-by-action replay as a correctness preflight, outside32 search/evaluation paths. No selected action may depend on validation outcomes. Publish score means/variance/visit counts and selection optimism, not only winners.

Environment foundation: pin all four runtime DLL hashes to E154 validation-v2, retain known unsupported Crystal Sphere(#64)/Trial(#294), fail on stderr exceptions. Old map certificates bind a different engine and arbitrary reward roots have no certified shortcut, so use verified full-prefix recovery for **all** roots; no silent fallback. Compare every restored response hash with the source prefix, then independently replay six preflight suffixes. This is bounded consistency/known-compatibility evidence, not universal/native engine certification (#297 remains separate).

Budgets: collection180s, bank/preflight240s, teacher900s wall and1800s aggregate parent+child CPU;8workers, local30s/300actions, full suffix90s/2400actions. Stop launching work on global budget exhaustion; retain unstarted/capped cases. Include restoration and actual engine transitions in costs. CPU may overshoot by in-flight bounded probes; overshoot fails the gate. Practical teacher latency gate: p95 serial discovery time per root <=60s (not amortized wall time).

Teacher gate requires all15 collection seeds/30roots and all probes/replays complete, audit/runtime integrity, budgets met; independent validation mean utility delta >=.05, 95% paired bootstrap lower bound >0 clustered by15 game seeds (10000 resamples,RNG149); >=5 seeds with positive mean delta; no negative mean in combat/preparation or A0/A5/A10; greedy local clear count and mean utility do not regress; greedy full-suffix Act2 arrivals do not decrease and no actor full victory is lost. This is an exploratory conditional teacher gate, not actor-only/full-game acceptance. If it fails, stop before E150. If it passes, E150 still needs its own frozen learning/holdout protocol. Final330 acceptance seeds remain unused.

## Reproduction

```sh
python3 -m unittest discover -s tests -p test_root_teacher.py
python3 scripts/pilot_root_teacher_e149.py plan --output artifacts/runs/e149-plan-v1.json
# Commit copied plan before collection; commit each result before next stage.
python3 scripts/pilot_root_teacher_e149.py collect --plan experiments/E149/plan-v1.json --output artifacts/runs/e149-collection-v1.json
python3 scripts/pilot_root_teacher_e149.py bank --plan experiments/E149/plan-v1.json --collection experiments/E149/collection-v1.json --output artifacts/runs/e149-bank-v1.json
python3 scripts/pilot_root_teacher_e149.py evaluate --plan experiments/E149/plan-v1.json --bank experiments/E149/bank-v1.json --output artifacts/runs/e149-evaluation-v1.json
```

Raw decisions, candidate distributions, plans, states and wire responses stay in ignored artifacts/runs. Public results retain compact outcomes and hashes. Frozen game version v0.111.0, dependency/model versions and exact tested SHAs are emitted by every stage.

## Natural collection v1

Tested `1137867fb89517b0102263e19cf557733534f3e7`: all15 new seeds naturally defeated, noAct2/Boss entry; median within-act floor9,max15. Collection 20.826s;18 raw bundles including3 complete independent replays audit exactly. All decision phases encountered, including76card-reward/32potion-reward/13rest/3shop decisions. Proceed to predeclared last-encounter/preparation bank, with no source resampling. These outcomes describe the frozen baseline, not search strength.

## Frozen bank / preflight

Tested `57419c55170be1902f86709dc5f3646cc7454112`:30 natural roots prepared in57.795s; six greedy continuations independently replayed action-by-action,12 bundles audited. Exact legal candidate sets and all raw-root hashes are frozen in bank-v1.json before search. Full-prefix responses are checked at every command. All game RNG remains fixed by the original prefix: sample variation is **continuation-policy randomness**, not a distribution over unknown draw piles. Teaching value is conditional on this underlying state; this experiment cannot certify privileged targets as unbiased values for a partially observed student. No native-rule certification is claimed.

## Evaluation v1 — incomplete, no teaching promotion

Tested `aaf71f7`:320.946s wall/704.262s parent+childCPU;8/30 roots complete,22roots time out.395raw bundles audit with no hash mismatch. Most later failures happen during process startup or full-prefix restoration, before root verification. The protocol fails execution and cannot establish the teacher's overall quality; do not discard those roots or report the8finished cases as a complete benchmark. No E150/training is started. A separate bounded execution diagnostic is required before deciding whether a scheduling-only rerun is warranted; preserve original outputs.

## Scheduling diagnostic protocol, frozen before execution

Replay exactly the original preflight plans for roots0,1,10,11,20,21 (combat/preparation at index000 of each difficulty), first with1worker then2workers.12paths total, each30s and240s global wall. Compare every prefix/suffix response and final state with the original six preflights; no new policy sampling. Only if all12match and each round p95path latency<=15s may a scheduling-only iteration rerun the same30roots. Keep the original v1 incomplete; new plan must preserve all seeds/candidates/streams/gates, change concurrency only, and report duplicate compute. These sequential rounds are confounded by host load/time, so they cannot prove concurrency caused the v1 slowdown. Command: `python3 scripts/diagnose_teacher_restore_e149.py --output artifacts/runs/e149-restore-diagnostic-v1.json`.

Scheduling diagnostic v1 at00a41c8 passes: all12 exact;1worker27.792s/p95case6.068s,2workers13.402s/p955.783s. Host state changed between rounds, so no causal attribution to concurrency. Two-worker throughput on these long reference prefixes could exhaust the unchanged900s teacher budget; preregister one additional fixed six-case4worker diagnostic (same30s/case,240s/global,all exact,p95<=15s). If it passes, use4workers for the identical complete30root rerun; only scheduling may differ, enforced against the original plan in code. No seed/stream/candidate/effect/latency/budget changes; v1 stays incomplete. Command: `python3 scripts/diagnose_teacher_restore_e149.py --workers 4 --output artifacts/runs/e149-restore-diagnostic-v2.json`.
