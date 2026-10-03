# E140 — Phase-aware network: offline AWR versus fresh PPO pilot

Objective remains the E139 reserved network-only Ironclad A0..A10 full-run acceptance, not single-battle wins. E139's126natural attempts all lost; only26Act2 entries and noAct3. The old encoder ignores context/next-boss/current macro menus. This pilot adds those observations and trains all decision phases before increasing RL scale.

Representation: retain the old276/144 features and append264state (8 numeric full-run signals+256semantic context/menu hash) and128action (upgrade/description and macro-option semantics). Explicit seed/run/time excluded. Shared S widths128/64, old weights transferred with zero new input columns so initial decisions match exactly; two source learner IDs1701/1702. No claim that this resolves all observation aliasing or substitutes for entity attention. CPU per E138 measured latency.

Fixed data: all60 E139 train runs (9041decisions, five heroes A0/5/10), never its development traces; E133 learner1701's updates29..32 (768 complete stochastic battle episodes), never validation/test. Audit source hashes. Initial BC:8epochs of phase-balanced sampling,128batch,Adam3e-4; half macro/half combat when available, no critic training on all-defeat full-run labels. Keep this BC model as control. Training-time imitation is permitted; final execution has no teacher lookup or override.

Offline arm: AWR-style replay, fit critic to complete battle Monte Carlo returns for4epochs; then4 actor epochs with exp((return-V)/.5) capped20, normalized perbatch; .25 macro-BC loss using64 train-only macro examples peractor batch. This is off-policy weighted regression, not PPO on stale log-probs and not a full reproduction of the paper. No new engine interactions in this arm; inherited E133 data cost reported separately.

Online arm: fresh on-policy PPO from identical BC weights,8updates×64terminal battles perlearner (512each). Each batch48Ironclad entries cycling E133train first/second/last plus all E139train Ironclad entries;16other-hero entries cycling E139train first/last and everyAct2 entry. Two learners1024total new training battles, eight workers,30s/120actions each, total1800s perlearner. Full-prefix restoration with exact entry checks; no native save assumptions, retries or incomplete rewards. Any incomplete episode skips the entire batch and stops that learner. Existing PPO gamma1/lambda.95/reward/hyperparameters retained; after each update apply4 batches of64 macro-BC at coefficient.1 and explicit metric. Mark arm PPO+macroBC, since it is a mixed objective; off-policy BC is never passed to clipped-policy-loss.

Freeze all final weight hashes and training report before evaluation. No checkpoint selection after test. Six arms (BC/AWR/PPO×two learners), plus oldE133long1702 neural-all and planner, on22new development seeds e140_eval_Ironclad_A{0..10}_{00..01},176 full attempts max. Same full-run limits asE139; first i=00 atA0/A5/A10 for each newarm (18plans) independently replay full path, including defeats. No E139 final reserved seeds used. Secondary: fixed E133validation early/challenging panels (not its old test). Report victories, Act2/3 reach, terminal outcomes, all errors, and local floor separately. Formal win objective primary; reaching farther is only diagnostic. Pilot continuation requires BOTH learner versions of an arm gain>=2Act2 arrivals/22 over ownBC, no fewer A0Act2 arrivals, and no censored execution. No default promotion without E139 final gate.

Synthetic encoder checks: changing act/floor/next-boss with otherwise identical data must affect new encoding; old frozen logits preserved under zero extension; variable menu padding remains legal; source test split never accepted by training loader. Synthetic checks are not gameplay evidence.

Research basis: [PPO](https://arxiv.org/abs/1707.06347), [AWR](https://arxiv.org/abs/1910.00177), [implementation sensitivity](https://arxiv.org/abs/2005.12729). Next alternatives stay separate: [Reanalyse](https://arxiv.org/abs/2104.06294) motivates search-improved targets using our exact engine; [IMPALA/V-trace](https://arxiv.org/abs/1802.01561) corrects actor lag, not an excuse for uncorrected replay; [Rainbow](https://arxiv.org/abs/1710.02298) is a dynamic-legal-action Q-learning alternative but needs target-network/offline extrapolation controls; [potential shaping](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf) requires correct terminal potentials. These are proposals, not results in this experiment.

Commands: `python3 scripts/pilot_fullpolicy_e140.py train --output artifacts/runs/e140-training-v1.json`; commit completed report/weights hashes; `python3 scripts/pilot_fullpolicy_e140.py evaluate --training experiments/E140/training-v1.json --output artifacts/runs/e140-evaluation-v1.json`.

## Iteration v1 failure

At f6c2c3c,24existing PPO tests and3new phase tests passed. The first BC checkpoint was written, then path metadata generation rejected a relative output path against absolute ROOT. No fresh gameplay or evaluation ran. Preserve checkpoint and exception log; BC curve was in memory and not recovered. Fix resolves output paths and persists each phase/batch. Restart the deterministic offline training as v2, preserving v1; online budgets unchanged. No policy or cohort change.

## Training v2 completed / weights frozen before evaluation

Training SHA `f77dead7922b413265bb2e07cd6c62cadf0cf0c1`. Two115,778parameter models;9041full-run BC examples, 12523 offline battle decisions from768previous episodes, and1024new terminal PPO battles (16642 transitions). Eachlearner completed8×64; no illegal/reset errors or censored episodes.1024new raw traces and843source bundles (including15source replays) separately audited. Totalv2wall559.927s including preprocessing and allBC/AWR/PPO phases; failedv1BCwork is retained separately and not included in thisv2timer. Offline/new-sampling budgets and distributions differ: candidate-system comparison, not a pure equal-compute algorithm ablation.

Allsix final weight hashes now committed, no validation-based selection. Ordinary PPO remains on-policy; offline AWR and auxiliary supervised macro updates are separate. Full-run evaluation uses only the frozen network with legal menus, no inference-time teacher.

Actual online curriculum counts: `{'Ironclad:Act1:A0': 258, 'Ironclad:Act1:A5': 258, 'Ironclad:Act1:A10': 252, 'Silent:Act1:A0': 32, 'Silent:Act1:A5': 32, 'Silent:Act1:A10': 24, 'Defect:Act1:A0': 14, 'Defect:Act2:A0': 14, 'Defect:Act1:A5': 16, 'Defect:Act1:A10': 16, 'Regent:Act1:A0': 14, 'Regent:Act2:A0': 10, 'Regent:Act1:A5': 14, 'Regent:Act2:A5': 6, 'Regent:Act1:A10': 16, 'Necrobinder:Act1:A0': 16, 'Necrobinder:Act1:A5': 16, 'Necrobinder:Act1:A10': 16}`. The first384Ironclad positions fall entirely within the E133 bank; new Ironclad Act2 entries appear in BC but not fresh PPO this pilot. Other-hero Act2 entries are sampled. This coverage limitation is retained, not silently reshuffled after training. Offline value targets remain single-battle returns, not full-run win probability.

Evaluation will also record custom-controller timing and fail its execution flag on secondary battle-validation errors; these are evaluation-accounting changes, no model or selection change.

## Evaluation v1 and decision

Tested SHA `9f7ac9b`;22 new independent game seeds ×8arms =176 complete full-run defeats (0 wins,0 censored).18preselected new-model full paths replayed exactly.288secondary battle-validation runs all terminal; all new arms clear24/24early entries.482raw bundles audit passed. Wall304.905s.

| Arm | Full victories | Reach Act2 | Reach Act3 | Prior challenging validation clears |
| --- | ---: | ---: | ---: | ---: |
| bc-1701 | 0/22 | 0/22 | 0/22 | 16/24 |
| awr-1701 | 0/22 | 0/22 | 0/22 | 14/24 |
| ppo-1701 | 0/22 | 1/22 | 0/22 | 14/24 |
| bc-1702 | 0/22 | 0/22 | 0/22 | 17/24 |
| awr-1702 | 0/22 | 1/22 | 0/22 | 16/24 |
| ppo-1702 | 0/22 | 0/22 | 0/22 | 15/24 |
| old | 0/22 | 0/22 | 0/22 | not rerun |
| planner | 0/22 | 5/22 | 0/22 | not rerun |

Execution passes. Both AWR and PPO continuation gates fail. Neither consistently improves Act2 reach by2/22 over its BC start; planner reaches Act2 in5/22, each neural arm at most1/22. Secondary single-battle validation also gives no consistent improvement overBC. E133's old long models previously scored17/24challenging; no old test set was reused here. Full-run wins, not floor or imitation loss, remain the objective.

Decision: retain optional full-phase encoder/BC/AWR/PPO comparison infrastructure and negative evidence; do not promote a default controller or automatically expand this recipe. The user's Ironclad A0..A10 network-only acceptance remains unmet, and330final seeds remain untouched. This is candidate-pipeline comparison with different sampling distributions/budgets, not an equal-compute causal proof that on-policy or off-policy learning is inferior.

Concrete remaining gaps: noAct3 training observations; fewAct2 observations and nonew IroncladAct2 PPO samples due fixed cyclic ordering; fullrun BC teacher never wins; current value targets still single-battle returns; legacy hash encoding loses entity/order/semantic detail. Ordinary decision responses omit the full map, but CLI already implements get_map — reuse it rather than rewrite it. Draw/discard contents remain missing, while exported Osty/orb_slots are omitted by existing encoders.

Next registered, unexecuted proposals: [E141 richer observation and existing get_map reuse](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/265), [E142 bounded exact-engine branch teachers](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/266). Establish teacher improvement before distilling its labels; never present selected training branches as legitimate one-shot full-run victories. No full-game dynamics model needs to be learned while the actual engine exists.

Artifacts: training-v1-failure.json preserves the initial metadata error; training-v2.json locks22local checkpoint files including6final candidate weights; evaluation-v1.json retains all176full runs,288validation battles and18replays. Raw game traces and weights remain ignored. No external model calls.
