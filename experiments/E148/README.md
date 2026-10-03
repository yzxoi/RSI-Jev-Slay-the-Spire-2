# E148 — Task-aware critic learnability under a frozen actor

Issue [#279](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/279). Hypothesis: adding the observed task goal, completed/remaining battles and ascension improves held-out prediction of the same frozen policy's six-battle return. This isolates input/critic learnability, not actor improvement, search quality or full-run wins. Existing E146 mixed-policy trajectories are diagnostic motivation, not training labels for a current-policy value.

## Frozen protocol (before collection/training)

- Behavior: original E146 source, E140 BC1702 checkpoint, exact path/hash read from `experiments/E146/training-v1.json`; stochastic actions sampled with the existing controller. All phases, including potions/rewards/cards/maps/shops, remain under this unchanged actor. No rule/search/LLM intervention. A separate observer logs only past/current progress; never future outcomes. No E141 rich inputs.
- New independent game seeds: `e148_{split}_Ironclad_A{asc}_{index:03}`; TRAIN asc=0/5/10,index0..71 (216); DEV asc=0/5/10,index0..23 (72). Two preselected action-sampling streams per game seed, giving432 TRAIN+144 DEV=576 trajectories. All repetitions of one game seed stay in its split. Sampling seed `148000000 + split_id*1000000 + asc*10000 + index*10 + repetition`, split_id0/1. No substitution or selection by outcome. Original final330 seeds remain unused.
- Stop: six genuine battle clears **after pending rewards**, on a living map, or natural defeat. Intermediate reward0; terminal reward−1 on defeat or1+0.25*HP/maxHP on curriculum clear. This is a six-battle research task, never a full-game victory. All errors/timeouts retained; any incomplete path fails execution and prevents training on a silently selected subset.
- Controls: independent critic copies of the same BC state trunk, reset value head; actor checkpoint untouched. Both arms allocate540+5 input dimensions and identical parameter count: legacy receives five zero inputs; contextual receives `[is_six_goal, target/10, completed/6, remaining/6, ascension/10]`. Goal type/length are constants in this pilot, so their extrapolation is untested. Copy the same initial trunk/head within each learner pair, train the critic trunk and value head only. Two shuffle seeds2101/2102; common minibatch order within each pair.
- Fixed optimization:24epochs,Adam3e-4,minibatch512,grad-norm1,CPU threads1. Loss is trajectory-balanced MSE: each trajectory has equal total weight; both arms share weights and data. No bootstrap, reward shaping, advantage normalization, actor gradients or checkpoint selection. Freeze final weights before DEV scoring. TRAIN curves do not choose a checkpoint.
- Simple baselines fit on TRAIN only: trajectory-balanced constant mean; ridge regression(alpha0.01,unpenalized intercept) on phase, completed battle count, difficulty, current HP ratio and progress interactions. Baseline inputs are current-state facts, not result labels. This is intentionally stronger than a constant critic and tests whether a neural critic adds value.
- Report trajectory-balanced MSE/RMSE,EV,R²,bias,per-phase/per-difficulty/initial/fatal/post-sixth-clear metrics,coverage,training curves,all case-level errors and hashes. Repeated states/paths are correlated. Pair bootstrap by game seed(2000 fixed resamples) for contextual−legacy MSE;72 DEV game seeds,not144 independent games. DEV greedy strength is not measured; stochastic policy is the same as collection.
- Gate: both learners must achieve >=10% MSE reduction vs paired legacy, >=5% reduction vs the better simple baseline, upper95% paired-bootstrap bound<0, no per-difficulty MSE increase>10%, and post-sixth-clear MAE<=0.25 and<=50% of legacy. Require at least10 distinct DEV game seeds contributing post-clear decisions; otherwise boundary calibration is inconclusive and gate fails. Gate failure stops automatic PPO expansion; gate pass permits a separately registered actor/search study, never default promotion.
- Budget:8 engine workers;collection900s,fit180s,evaluation120s (total<=1200s measured stage time; engineering excluded). Per-path180s/2400actions existing safety caps. Six preselected independent replays: each split×difficulty,index0,repetition0,regardless of outcome. No native game or overlay actions. Before fitting, commit the complete dataset/config/raw-trace manifest. Before DEV scoring, commit the frozen weights manifest.

Implementation commits precede their evaluations; preserve every failed attempt. Publish compact metrics/hashes, retain full traces/tensors/weights in ignored `artifacts/runs/`. Decide from this fixed gate, not from a favorable phase or one learner. This diagnostic may expose limitations of the legacy representation without identifying a single cause of full-run failure.

Before fitting/DEV scoring, add one descriptive statistic on the already fixed two-rollout design: require identical starting critic inputs for both repetitions and estimate starting-return sampling variance as mean((G1-G2)^2/2). Compare only to initial-state MSE, never whole-trajectory MSE, and do not change the gate or remove cases. Finite-sample estimates can be noisy. Synthetic test development initially omitted gold/HP from a reward-boundary fixture; that fixture was corrected (including potion-generated in-combat rewards), then all4 contracts passed. No game attempt was affected.

Collection v1 at47c7e15 completed all576 paths and wrote all per-case results and tensors, then failed during publication because a relative output path was passed to Path.relative_to(absolute ROOT). Preserve log/tensor hashes in attempt-v1.json. Repair normalizes CLI paths and reconstructs every original tensor row from existing raw wires/actions/task metadata; no rerun or replacement. Recovery has180s read-only budget. Charge the full900s collection allowance conservatively including recovery, report actual trace span/recovery separately (initial setup/serialization wall time unavailable after the exception). Four synthetic contracts had passed before collection.


## Results: gate failed; keep actor and default policy unchanged

- Frozen collection code47c7e15, recovery codee6d53f9;288 new game seeds,576 trajectories,51,343 decisions. TRAIN432paths/216seeds:55six-battle clears,377natural defeats;DEV144paths/72seeds:18clears,126defeats. A0/A5/A10 TRAIN clears36/15/4 of144each;DEV11/7/0 of48each. These are the unchanged stochastic BC actor's **curriculum** outcomes, not new policy or full-game wins.
- Six preselected independent replays match.582raw bundles pass. After the publication-path exception, all51,343 stored observation/task/phase/target rows were reconstructed exactly from the original576raw traces; tensor hash7797e697ed8b71f5fbb76e919ed9a67d953d127c846aa9ec1de54b32cf838976 unchanged. No resampling or substituted seeds. Complete frozen evidence in bank-v2.json.
- Critic fit code04af5af;four independent86,529parameter critics,24epochs each;no actor updates. Weights frozen at51a95e7 before DEV scoring. Fit13.919s;DEV evaluation code51a95e7,1.721s. Source actor hash unchanged;DEV rows used for fitting0. Original collection trace span288.972s(excludes setup/serialization),read-only recovery26.458s;conservatively charge the full900s collection allowance, stage total915.640s. Post-gate read-only diagnosis0.751s is separate and performs no training/gameplay.

| Predictor | TRAIN balanced MSE | DEV balanced MSE | DEV post-clear mean V |
| --- | ---: | ---: | ---: |
| Constant |0.4877|0.4799|−0.7334|
| Progress ridge |0.4068|0.4104|−0.1647|
|2101 legacy|0.0651|0.5633|−0.3651|
|2101 task|0.0626|0.5385|−0.3544|
|2102 legacy|0.0663|0.5664|−0.4186|
|2102 task|0.0644|0.5465|−0.3968|

True mean post-clear DEV return+1.0938(28decisions across18trajectories/16game seeds). Context reduces aggregate MSE4.40%/3.51%,less than the10%gate, and remains worse than both simple baselines. Paired per-game-seed95%bootstrap intervals for task-minus-legacy MSE are[−0.05085,−0.00410] and[−0.04355,−0.00028]: small positive evidence, not a sufficient practical gain. Both pass paired/difficulty/coverage checks but fail legacy-effect-size,simple-baseline,andboundary-calibration gates. Final expansion_gate=false.

The central diagnosis is poor generalization: on TRAIN post-clear states, task critics predict+1.023/+1.002 withMAE0.162/0.197;on unseen states−0.354/−0.397 withMAE1.448/1.491. Task inputs have nonzero sensitivity,so they were not disconnected;zeroing them is out-of-distribution and only a sensitivity check,not a causal game test. Gains concentrate inA10,where every DEV path fails;improved pessimism there is not evidence of improved winning ability.

Initial-state paired-return noise estimate0.43045,versus task critic initialMSE0.64531/0.63558 andridge0.44913. This descriptive estimate applies only to identical initial inputs,has sampling uncertainty,and is not a whole-trajectory noise floor. All return observations remain,including stochastic failures. The strong train/DEV gap and simple-baseline advantage justify stopping this neural fitting recipe;they do not prove all neural values or PPO are ineffective.

Decision: merge isolated diagnostic tooling/data/negative result,not a gameplay policy. No expansion of this critic/PPO recipe and no automatic use of these critics as search leaves. E149 remains the next separately bounded question: real repeated continuations must demonstrate a better teacher before E150 distillation. Current input repair alone is insufficient. Final330 acceptance seeds unused. See [report and figure](../../docs/research/learning-search/2026-10-03-task-value-pilot.md).

```bash
python3 -m unittest discover -s tests -p test_task_value.py
python3 scripts/probe_task_value_e148.py plan --output artifacts/runs/NEW-plan.json
# Freeze the plan in Git before collect. Use new paths; existing evidence is never overwritten.
python3 scripts/probe_task_value_e148.py collect --plan experiments/E148/plan-v1.json --output artifacts/runs/NEW-bank.json
# Freeze bank JSON in Git before fit, and final training manifest before DEV evaluation.
python3 scripts/probe_task_value_e148.py fit --bank experiments/E148/bank-v2.json --output artifacts/runs/NEW-training.json
python3 scripts/probe_task_value_e148.py evaluate --bank experiments/E148/bank-v2.json --training experiments/E148/training-v1.json --output artifacts/runs/NEW-evaluation.json
python3 scripts/plot_task_value_e148.py --training experiments/E148/training-v1.json --evaluation experiments/E148/evaluation-v1.json --output artifacts/runs/NEW-figures
```

Post-gate diagnosis atbf05f06: `python3 scripts/inspect_task_value_e148.py --output artifacts/runs/e148-diagnosis-v1.json`; no checkpoint selection or gate changes. Figure inspected;4synthetic contracts pass. Historical publication failure remains in attempt-v1.json/commits. Local matrix,predictions,weights,and rawtrace stay ignored;public manifests preserve hashes. Runtime M3MaxCPU/Python3.13.5/torch2.11.0/numpy2.3.2/.NET9.0.318/historicalv0.111.0,with exact DLL/adapter/patch hashes in manifests.
