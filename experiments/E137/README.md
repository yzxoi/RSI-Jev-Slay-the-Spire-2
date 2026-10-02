E137 — Audited pre-decision reset retry and exact PPO checkpoint resumption

Problem: E133 v1 S1701 update14 train-094-b7 timed out inside load_save before entry verification and before any policy decision. It had passed certification/earlier uses. Whole batch skipped and learner stopped, preserving13 updates. S1702 stopped update1 on a separate191-choice menu bug (E136).

Hypothesis: preserve all failed evidence, resume only from completed optimizer checkpoints, and allow at most one explicit fresh-process retry for a narrowly verified pre-decision load timeout. This enables the fixed training budget without treating errors as losses or selecting favorable outcomes. Do not patch engine or claim to solve the intermittent native-load stall root cause.

Retry scope: only status timeout, steps0, entry_verified=false, no decisions/data/reward, audited wire containing ready and exactly one load_save command with no response; previous process closed. Same checkpoint bytes, expected map/entry, model, sample seed and restore mode; one additional attempt, shared original30s episode and learner remaining3600s budget. No retry for action/selection errors, mismatches, gameplay timeouts, defeats, caps or uncertain live actions. Record both attempts and all resource costs. Evaluation remains no-retry unless separately declared; this experiment is training collection only.

Resume: freeze source E133 v1 report and all weight hashes first. Carry only contiguous completed updates; preserve interrupted batch in source/explicit metadata. Reload model+Adam exactly. Reconstruct NumPy shuffle RNG from learner seed and the recorded epoch/permutation counts (including KL early-stop boundary), prove this against uninterrupted synthetic PPO training with exact model/optimizer/RNG equality. Persist RNG state in new checkpoints. Resume update14 for1701, update1 for1702; rerun each entire interrupted192-case batch, no sample replacement. Original failed work counts against learner3600s budget; maximum32 optimized updates/6144 episodes each including inherited updates. No new model/seed/reward/selection/test gate. Inherited short checkpoint validations are reusable only where source states/candidate menus are compatible with E136; verify this.

Preflight before any resumed gradients: real original train-094-b7 save reset three fresh processes, full-prefix replay of their actual final trajectories; source failure audit; no claim the historical timeout never occurred. Exact same frozen S1701 update13 sampled batch member. Synthetic injected loader timeout proves exactly-one retry and shared deadline; forbid post-entry retries/mismatches. All gates must pass, <=300s compatibility phase. Then separately recorded E133 v2 resumption under original effective budgets. Gate failure retains evidence and stops; no recursive retry/budget extension. Merge only after compatibility/resume tests and audit pass.

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/257

Resume adds a real consistency gate before the first resumed optimizer step: every previously terminal member of each interrupted batch must reproduce its original transition/final hashes under the same weights and sampling seeds. All191 old terminal members per affected learner are retained; the one failed member must now complete legitimately. E136's committed proof and an audit of all inherited card-selection menus must pass before allowing inherited updates/validation selections. New checkpoints save the exact shuffle RNG state.

## Compatibility result and merge decision

Tested SHA `8d53dd6`.29 focused synthetic tests passed, including exact model/Adam/shuffle-RNG equality after serialization/resumption, KL early-stop epoch boundary accounting, strict retry eligibility, one attempt maximum and shared deadline. Source inherited2640 episodes/44832 decisions were checked; all712 actual card-selection menus remain byte-identical under E136. The committed source training report and3024 raw bundles audited.

The exact original train-094-b7 /S1701 update13 weights /update14 sampled seed reset successfully in three fresh processes; all three sampled battle clears had identical trajectories, and all three independent full-prefix replays matched. Seven original/new trace bundles audited;24.628s. This does not erase or solve the original intermittent loader stall.

```sh
python3 -m pytest tests/test_ppo_resume.py tests/test_ppo_actions.py tests/test_ppo.py tests/test_ppo_bank.py tests/test_ppo_scale.py tests/test_research_restore.py -q
python3 scripts/validate_ppo_resume_e137.py --output artifacts/runs/e137-validation-v1.json
```

**Merge:** the narrow reset-retry and exact-resume compatibility gates passed. Enable only for the explicitly requested E133 resume path. Native save bytes and engine hashes unchanged. Mid-battle errors, state mismatch, defeat, caps and other timeouts are never retried. No playing-strength evidence from this compatibility case.

**E133 v2 amendment before resumed gradients:** source `experiments/E133/training-v1.json`, original623-entry certificate and same264-seed bank; use E136 complete selections with unchanged features/weights. Resume1701 after13 optimizer steps and1702 after0. Rerun entire interrupted192-case batches with fixed original sample seeds and require every previously terminal member's full trajectory equal before optimizer update. Preserve original failed batches by immutable source reference; charge original800.340/53.763 workseconds against the same3600s learner ceiling. Stop at32 total optimized updates each, not32 additional; effective model training ceiling remains6144 episodes each, with attempted/retried episodes reported separately. Original checkpoint validation ranks and held-out gates unchanged; no test policies evaluated yet. A new report v2 includes inherited evidence and current session costs. No additional training-budget extension is authorized by this amendment.
