# E133 — Checkpoint-backed multi-ascension PPO retraining

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/250

Status: both retraining replicates completed; selected weight hashes locked before held-out evaluation.

## Objective and hypothesis

The user authorized retraining with more data after E132 proved reusable natural battle-entry saves. E133 tests a larger, harder multi-ascension training distribution at unchanged 73,794-parameter PPO capacity and four times E127's episodes per learner. This jointly changes data coverage and training duration; it is not E131's isolated matched-budget curriculum experiment, which remains unexecuted. No promise of full-run mastery.

## Fixed inputs and preparation

Historical official v0.111.0 and unchanged pinned adapter/DLL hashes. Ironclad only; 192 train / 24 validation / 48 test independent seeds named `e133_20261002_{train,val,test}_{000..N-1}`. Each seed is assigned ascension `(0,5,10)[index % 3]`, with no reuse across splits. Same E120 resource-aware preparation planner and macro policy. Naturally advance until the first Elite or Boss combat entry, or eighth combat entry, or real death, whichever comes first; 120 seconds / 1,200 actions per seed, eight engine workers. Preserve every selected seed, all intermediate entries, deaths, errors, caps and unavailable later rooms; no replacement or state/RNG editing.

Freeze the full preparation bank before continuation validation. Training uses the unique first, second and last available entries from each seed, cycling `(update-1+seed_index) % eligible_count`. Validation/test panels use second-available (early) and last-available (challenging), preserving duplicate panel identities and reporting them as correlated, not extra seeds. Count encounter/difficulty/resource coverage before training. A seed with no entry, an actual preparation error/cap, or fewer than eight distinct training encounter signatures stops this batch; real preparation deaths with earlier entries remain usable and reported.

## Native restore validation and fallback

Add explicit optional checkpoint reset to the existing PPO episode runner; full-prefix restoration remains the default. For each eligible train/validation entry whose immediate preceding state is a true Map boundary: A runs the unchanged planner from full prefix to battle terminal; B independently repeats the prefix, writes a native Map save, verifies the A action/transition path and extends through rewards to the next combat second-turn opening or real death; C1 independently loads the unchanged save and exactly replays B's extended path; C2 uses the actual PPO episode checkpoint reset to replay A's battle path. Require exact map/entry/all before-after/final hashes and unchanged save bytes/native seed/ascension. Each path <=30 seconds / existing 120 battle actions, extension <=80 actions. For natural event-combat entries with no immediate Map boundary, retain explicit full-prefix mode and require an independent full-prefix A replay; do not edit coordinates or silently drop them. Save/correctness failures stop training rather than substituting a faster path. Every native index is bound to bank/engine/evidence hashes.

Validate training/validation restoration first; defer held-out test-policy continuation results until all selected weight hashes are committed. Training/validation preparation and certification have a 30-minute phase budget: stop launching new jobs at expiry, preserve unstarted work. No game-engine patches or warm-worker reset in this experiment.

## Training budget and fixed selection

Two fresh learner initializations 1701/1702, S widths 128/64 (73,794 parameters), unchanged E127 encoder, terminal reward, optimizer/PPO hyperparameters. No search, reward shaping, imitation, network widening, future/seed inputs or external model API. Each learner: 32 updates × 192 terminal episodes = 6,144 episodes maximum; both learners total 12,288. CPU Torch single-thread, eight engine workers; <=3,600 collection/optimization seconds per learner. Each episode <=30 seconds /120 actions. Stop the affected learner on any incomplete training episode, skip the entire affected update and retain all traces; censored episodes never get an invented reward. No automatic additional budget.

Checkpoint every update; greedy fixed validation at updates 0/8/16/24/32 on BOTH early/challenging panels. Rank by challenging clears, challenging mean reward, early clears, early mean reward, earliest update; selection requires all panel outcomes terminal and no real execution error. Freeze two selections per learner: short-budget best among 0/8 (<=1,536 episodes), and long-budget best among 0/8/16/24/32 (<=6,144 episodes). Both may select the same checkpoint; do not force a late checkpoint or conceal regression. Record every failed checkpoint/validation/cap and raw learning curve.

## Held-out comparisons and exit rules

After selected hashes are committed, certify the test reset paths and evaluate all 48 preselected test seeds on both panels. Arms: planner, attack-priority, corresponding two frozen E127 S models, E133 short and E133 long models for each learner. Independently full-prefix replay every terminal E133 model trajectory, including losses; identical selected weights may reuse the exact already-evaluated record with explicit alias metadata (no invented extra samples).

Execution gate: bank/evidence/engine hashes intact, no illegal/reset/transition errors, no censored selected-model test outcome, all independent replays exact. Report all panel and difficulty cells, preparation reachability and duplicated entries; 48 is the independent test-seed count, not 96 panels or the number of learners.

Practical improvement gate for BOTH long learners: at least +3 challenging clears /48 over the corresponding E127 S; challenging paired HP-equivalent median >=+2 (legitimate defeat=0, censored unscored); preserve early A0 clears and early A0 median HP delta >=-2; match or exceed planner challenging clears. Separately, longer-training evidence requires BOTH long selections to gain at least +2 challenging clears and median HP >=+2 over their own short selections, without fewer early clears. No training-strength conclusion from loss alone. If gates fail, retain evidence and stop expansion; no silent seed/reward/network change or default real-game promotion.

## Deliverables and limits

Versioned issue/PR/commits, exact code SHAs and commands, compact machine-readable reports, native-save/trace/model hashes, loss/value/entropy/KL and train/validation reward curves, difficulty/panel held-out results and resource/throughput costs. Raw traces and weights local ignored; never proprietary binaries/secrets. Update research/decision records and private Notion. This learns combat from planner-prepared routes/decks/rewards, not end-to-end deck-building/full-run play. Initial model remains small so data and restoration are the focus; broad character training is separate.

## Preparation v1

Implementation/freeze SHA `e3ae398`; 14 synthetic PPO, split/selection and checkpoint-reset tests passed. Commands:

```sh
python3 -m unittest discover -s tests -p 'test_ppo*.py' -v
python3 scripts/retrain_ppo_e133.py freeze --output artifacts/runs/e133-fixtures-v1.json
```

All 264 selected seeds retained: 224 reached the planned boundary; 40 naturally died after providing earlier entries. No preparation errors/caps or seed replacements. Preparation took 133.287 seconds; 264 raw bundles hash-audited. The training subset has 575 unique first/second/last entries, including 423 Monster / 151 Elite / 1 Boss; 29 ordered exported enemy-list signatures, 423 deck hashes, 198 entries with potions; HP min/median/max 1/64/91. Ascension entry counts A0/A5/A10 = 192/191/192 (one seed has only two distinct positions). 574/575 training entries have an immediate true Map boundary, one retains explicit full-prefix mode. This is much broader than E127's 191 Monster + 1 Elite entries, but preparation survival and conditional battle skill remain distinct.

After freeze execution started, separate commit `735fa81` added plotting and corrected inherited episode trace scope metadata to E133; no game-policy or freeze changes. Native reset certification uses the next clean committed version. PR #251 attachment was attempted; Codex rejected it because this thread exceeds 100 attachment identities. GitHub PR remains available.

## Certification v1 — failed; no training started

Code SHA `7046576ab533f3b3b80ffcb73d88c5bec110da92`; 623 eligible training/validation entries checked in 784.463 s, with 2,477 raw traces audited. 611 native certifications and one predeclared non-Map full-prefix entry passed; eleven records failed. Ten native failures involve entry or later continuation mismatches (including Unknown-room resolution); one genuine headless error at `train-150-b8` occurs after Colorless Potion selects Rolling Boulder: missing GodotObject.Connect(StringName, Callable, UInt32) during RollingBoulderPower.AfterPlayerTurnStart, then end-turn timeout. The training gate is failed and no optimizer was run.

All failed cases, frozen before further evaluation: train-019-b5, train-044-b2, train-090-b8, train-097-b2, train-102-b2, train-113-b5, train-129-b5, train-131-b2, train-150-b8, train-155-b6, val-009-b3.

Separate [E134 #252](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/252) tests explicit full-prefix reset recovery without deleting samples or silently retrying native saves. It must block on the genuine engine failure; that requires a separate compatibility fix. Any E133 v2 protocol/engine change must be recorded before another evaluation; data/model/reward/selection/test gates remain fixed unless explicitly amended.

## v2 compatibility amendment before recertification/training

E135 PR #255 passed and merged into the dependent compatibility branch: exact original Rolling Boulder mechanics now run; all 264 preparation histories / 23,498 actions / 1,460 entry states are unchanged. Switch BANK to the separately committed fixtures-v2.json, bind all reset evidence to the new adapter and Godot stub hashes, and rerun all 623 training/validation certificates. Every native-incompatible case then undergoes the fixed E134 full-prefix proof; runtime errors still block. v1 failed certifications remain intact. Each v2 certification/recovery is a separately timed batch, not included retroactively in the failed v1 budget.

No changes to sample IDs, preparation choices, network, learning settings, reward, learner seeds, episode/work budget, checkpoint selection or test gates. Baseline E127 weights retain their original file/bank/encoder/runtime checks, then transfer explicitly to the repaired evaluation adapter only with the committed E135 exact-history equivalence proof. Test records disclose source and actual runtime hashes. No historical evaluation is relabeled or replayed with falsified runtime metadata.

## Certification v2 — original engine error resolved, native failures retained

Tested SHA `97ec4c1`; 623 entries, 785.361 seconds, all 2480 raw traces audited. 612 native + one predeclared full-prefix entry passed. The same ten native continuation mismatches remain: train-019-b5, train-044-b2, train-090-b8, train-097-b2, train-102-b2, train-113-b5, train-129-b5, train-131-b2, train-155-b6, val-009-b3. `train-150-b8` now passes all A/B/C1/C2 paths, including genuine battle clear. No new engine errors; the all-native gate remains explicitly failed. Freeze this complete result before E134 v2 recovery. No optimizer has run. 24 focused PPO/scale/bank/fallback/restore tests pass; original E127 S1701/S1702 weights loaded with the audited migration proof, without policy evaluation on the held-out set.

```sh
python3 scripts/retrain_ppo_e133.py certify_train --output artifacts/runs/e133-certificate-train-v2.json
python3 -m pytest tests/test_ppo.py tests/test_ppo_scale.py tests/test_ppo_bank.py tests/test_reset_fallback.py tests/test_research_restore.py -q
```

## Training v1 — incomplete batches preserved; test remains locked

Training SHA `383da286fa4402083b327a1c698bf6bac71e492b`. Results: `[{"learner": 1701, "updates": 13, "optimized_episodes": 2496, "attempted_episodes": 2688, "work_seconds": 800.3398571661673, "status": "invalid"}, {"learner": 1702, "updates": 0, "optimized_episodes": 0, "attempted_episodes": 192, "work_seconds": 53.76325754215941, "status": "invalid"}]`. All 3,024 raw trace bundles audited. Learner 1701 made 13 valid updates (2,496 optimized episodes); update 14 had one load_save timeout before entry/any policy action, so the entire batch was skipped. Learner 1702 update 1 reached a legitimate 19-card choose-up-to-two selection (191 possibilities), but the inherited macro candidate cap returned 128; encoder correctly rejected truncation. Its entire batch was skipped and no gradient update performed. Both stop conditions held. No held-out model evaluation or successful long-training claim.

Learner 1701 fixed validation at 1,536 episodes: early 24/24 (initial 14/24), challenging 16/24 (initial 3/24); challenging A0/A5/A10 = 7/8, 6/8, 3/8. These are validation results, not independent test results or comparison to E127/strong planner. Original failed batches and weight checkpoints retained; fixes require atomic compatibility experiments and a declared resume policy before another training iteration.
**E133 v2 amendment before resumed gradients:** source `experiments/E133/training-v1.json`, original623-entry certificate and same264-seed bank; use E136 complete selections with unchanged features/weights. Resume1701 after13 optimizer steps and1702 after0. Rerun entire interrupted192-case batches with fixed original sample seeds and require every previously terminal member's full trajectory equal before optimizer update. Preserve original failed batches by immutable source reference; charge original800.340/53.763 workseconds against the same3600s learner ceiling. Stop at32 total optimized updates each, not32 additional; effective model training ceiling remains6144 episodes each, with attempted/retried episodes reported separately. Original checkpoint validation ranks and held-out gates unchanged; no test policies evaluated yet. A new report v2 includes inherited evidence and current session costs. No additional training-budget extension is authorized by this amendment.

## Training v2 complete; weight selection locked before held-out continuations

Resume/training SHA `ee3f06f4b591b7ff0b9077aa45edb1c6c235d980`. Both learners completed32 optimizer updates /6144 episodes each, **12288 effective episodes /196445 optimized transitions** total, at73794 parameters each. All382 previously terminal trajectories from the two interrupted batches matched exactly before their resumed optimizer updates. No automatic reset retry occurred in this v2 training. Effective training+validation audit:12768 raw bundles, zero failures; original384 rejected-batch attempts remain in separately committed v1, not counted as optimized episodes.

Cumulative collection/optimization (including original failed work):1701=1818.552s,1702=1753.795s. Cumulative training plus validation:1897.577+1827.924=3725.502s (62.09min). Actual optimizer work:16.457+15.410=31.867s. Thus sampling/restoration still dominates; no paid model API calls. Source phase hashes, raw traces and all66 checkpoint hashes retained; binary weights local ignored.

| Learner | Short selection | Long selection | Challenging validation at0/8/16/24/32 | Early validation after training |
| --- | --- | --- | --- | --- |
|1701|update8 /1536 episodes|update24 /4608 episodes|3/16/17/17/16 out of24|24/24 at all trained checkpoints|
|1702|update8 /1536 episodes|update32 /6144 episodes|6/14/17/17/17 out of24|24/24 at all trained checkpoints|

The last1701 checkpoint regressed and is not selected. Both learners' best challenging validation counts remain below the original same-entry planner's19/24; these validation observations are not the independent test result. The48 held-out seed policy continuations remain unrun as this selection is committed.

```sh
python3 scripts/retrain_ppo_e133.py train --resume experiments/E133/training-v1.json --certificate experiments/E134/recovery-train-v2.json --output artifacts/runs/e133-training-v2.json
```
