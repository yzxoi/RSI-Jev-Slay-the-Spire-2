## Hypothesis

A frozen PPO policy prior plus learned value can improve battle decisions with bounded PUCT search; value estimates must be tested against actual policy rollouts, not assumed useful because training MSE falls.

## Fixed experiment

Depends on valid selected E127 checkpoints. Use both L learner seeds 1701/1702 regardless of their relative validation ranking, on every one of the same 24 E127 held-out third/last-available battle entries. This reuses a test cohort for a preregistered inference contrast, not a new independent replication. Freeze this protocol before E127 test outcomes.

Arms per model: direct greedy policy (E127 result), PUCT with learned leaf value, PUCT with greedy actor continuation to terminal. Same frozen actor priors and 16 simulations per root, c_puct=1.5, maximum depth=8 primitive game actions, first-play urgency=parent normalized value; root action chosen by visits, then Q, then prior, then stable candidate index. Normalize reward [-1,1.25] to [0,1]; clamp only nonterminal predictions, never change terminal reward. No alternating-player sign flip in this single-player game. No Dirichlet noise, temperature, hand-written action score or test-selected hyperparameter.

Invoke search only at the first combat_play decision of each new round, for the first six rounds. Other decisions (including generated card selections) use the same greedy actor; a simulation may traverse those selections normally. Each simulated edge runs in a fresh official-engine process from the canonical prefix plus exact observed committed history, with hash checks on every replayed continuation. Cached tree observations are per action path, not merged by partial observable hash; repeated terminal/maximum-depth leaves may be reused without charging an engine reset, but still count as simulations. No snapshots, RNG/HP edits or engine modifications. At most 96 simulations per battle. Each simulation 15 seconds/120 rollout actions, each root 60 seconds, each searched battle 240 seconds/120 executed actions. Four battle workers (at most eight processes counting live and probe); fixed 24 seeds, no replacements.

If any probe hits a cap or actual transition error, mark the search incomplete/error, abort that battle rather than silently substituting a baseline. Retain all traces including failed search; caps are censored, not defeat. Replay each final complete searched trajectory independently from the full prefix, without search, and require all before/after hashes and terminal results to match. Learned policies remain frozen. Search episodes are not fed into PPO; this is not AlphaZero training.

## Measurements and exit

Report exact statuses, paired clears/final HP/potions vs direct policy and planner, root choices/visit counts/Q/priors/depth, search-changed decisions, total wall/reset/inference times. In rollout arm compare predicted leaf value with its exact greedy-continuation return as a diagnostic (different rollout allocation means calibration is not paired across the two tree arms).

Continue toward search-guided training only if BOTH value-search models preserve direct-policy clears and improve median paired HP by >=3; preserve planner clear count and lose no more than median 2 HP; all 48 selected trajectories replay exactly and no execution/cap errors. Prefer neural leaf evaluation over terminal rollouts only if no lower clear count, median HP >= -2 versus rollout search, and median battle wall time <=75% of rollout arm. Fixed budgets, no post-result enlargement. Otherwise preserve negative findings, diagnose critic ranking/coverage or restore overhead, no live default promotion.

## Implementation and preflight protocol

Issue #243. Before test, run synthetic single-player backup/depth/cache checks and a real-engine preflight on fixed validation entries val-00/val-01 with L-1701, both search evaluators, plus exact full-prefix replays. This preflight diagnoses implementation only; no hyperparameter selection. A real error blocks formal test until a separately committed fix and fully recorded repeat. Training is E127; frozen search creates no gradients.

The implementation allows preflight as soon as the preregistered L-1701 learner has completed and selected its final checkpoint, while the independent second learner finishes. Formal test still requires all four valid E127 training runs. Preflight and test must match the exact selected L-1701 record, including weight SHA, widths and update. This changes scheduling only, not search parameters or validation/test inputs.

Preflight checkpoint committed before evaluation: `artifacts/runs/e127-training-v1/L-1701-24.pt`, SHA256 `bc310bcf3df545b40f459f0583c52273821ade0e885c12c7ab806529b2267cd5`. Three synthetic PUCT checks passed at `1c56dde`. Added descriptive calibration against assuming a clear at current HP; this is not a gameplay control and does not change selection or any gate.
