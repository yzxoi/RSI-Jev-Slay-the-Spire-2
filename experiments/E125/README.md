# E125: bounded masked-PPO battle-learning pilot

Issue: [#238](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/238). PR: [#239](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/239). **Completed; automatic continuation gate failed.** V1 entry preparation failed; explicitly amended v2 trained two small PPO models. Both clear all 16 held-out first combats but lose median 6 HP to the planner, outside the preregistered 5-HP tolerance. One initial-policy result is censored. Retain optional research tooling and negative evidence; no default-policy change or extra training.

## V2 amendment, frozen before any training

At SHA `888b74a88e593357f17dcf0b6249e40bf11366ac`, six synthetic checks passed, but the original 40-seed fixture batch produced only 35 target entries; the fixed pre-entry controller died on `train-04`, `train-08`, `train-10`, `val-05`, `test-01`. All 40 traces audited. The reused E120 entry predicate also accepts a Boss when no Elite was reached (five surviving cases), so v1 did not implement an exclusively Elite benchmark. Preserve the failed batch in `fixtures-v1.json`; **v1 stops without training or policy-strength results**. No failed seed is removed or replaced.

Before observing any learned policy, change the scope for **every one of the same 40 seeds** to its first natural combat. Extract the shorter canonical prefix/entry from the original hashed wire logs, freeze/commit this new bank, and independently replay validation entries before training. Existing raw traces may contain later actions, but the new episode reset replays only the prefix to first combat. All train/validation/test membership, PPO settings, learner seeds, selection rules, budgets and strength gates remain unchanged. This is a simpler feasibility pilot, not a pass of the original Elite-entry gate; results cannot establish Elite/Boss or developed-deck strength. No default controller or game engine changes.

The remainder records the original v1 protocol verbatim where it mentions Elite; this amendment defines the actual v2 training scope. Preparation outcomes from test seeds were seen; learned-policy test outcomes remain sealed until checkpoint selection. The post-v1 scope change is disclosed and all seeds are retained.


## Objective / hypothesis

Test whether a small learned policy/value network can improve battle decisions on unseen game seeds enough to justify more training. Compare from-scratch PPO with its untrained initialization and the existing deterministic `legacy`/early-potion planner. No MCTS, LLM, imitation warm start, engine edits or live-game writes. This is a battle-learning pilot, not full-run strength or high-ascension validation.

## Frozen scope and inputs

- Historical game v0.111.0 and existing pinned headless DLLs, no rebuild.
- Ironclad, A0, first reachable Elite using unchanged E120 macro/control policy up to entry. Prefix generation includes legitimate Neow/rewards/cards/routes. Learner controls every combat/selection/potion action until the first true battle terminal boundary; battle-generated card rewards are not terminals.
- New game seeds: `e125_20261002_train_00` through `_15` (16), `e125_20261002_val_00` through `_07` (8), and `e125_20261002_test_00` through `_15` (16). No replacement of unavailable entries; fixture failure stops the pilot with all 40 selected cases reported. No old E120 entries as training examples.
- Full canonical prefix reset in a fresh engine process with exact exported entry-hash checks. Do not extend E121 snapshot certification to untested states. Four workers; 90 seconds / 700 actions to capture each entry; 30 seconds / 120 actions per battle. A timeout/action cap is censored, not a loss. Any actual compatibility or transition error stops that training replicate; do not train on incomplete episodes or silently substitute cases.

## Learning implementation

- Small shared state encoder and per-candidate actor, scalar value head. Fixed structured numerical features plus deterministic hashed categorical/entity features; no seed, trace ID, future outcome, policy/planner score or action-index labels as model inputs. Variable candidate sets, padding masked both during sampling and PPO update. Unsupported/truncated candidate enumeration fails closed. Public features describe observations, not a claim of full hidden-state access.
- From scratch PPO-Clip: learning rate 0.0003, clip 0.2, gamma 1, GAE lambda 0.95, four epochs, minibatch 128, entropy coefficient 0.01, value coefficient 0.5, gradient norm cap 0.5, target approximate KL 0.03. Fixed CPU execution and recorded PyTorch/NumPy versions. Fully completed episodes supply Monte Carlo boundaries and GAE; no bootstrap through death or resets. Shuffle minibatches only, never test seeds into training.
- Reward: zero intermediate reward; terminal defeat -1; terminal clear `1 + 0.25 * HP/maxHP`. This is an explicit battle-survival/resource proxy, not the final full-run objective. Potions may be spent without a conservation bonus in this first pilot; resource use remains measured. No hand-shaped damage/progress reward.
- Two learner seeds: 1701 and 1702. Each at most 12 updates × 32 episodes (each train seed twice per update), or 1,200 seconds for training collection/optimization. Finish only an in-flight bounded batch if the wall budget expires. All raw episode evidence/model checkpoints retained locally with published hashes; each iteration/update records loss, entropy, KL, invalid actions, terminal returns, compute/engine time and exact tested SHA.
- Greedy validation after updates 0, 4, 8, 12 (only reached checkpoints). Select by validation clear count, then mean terminal reward, earlier checkpoint on ties. Freeze selected checkpoint hashes before opening test outcomes. Never select by test results.

## Verification and evaluation

- Synthetic tests: padding masks and permutation behavior, GAE terminal boundaries/known returns, clipped surrogate arithmetic, finite useful gradients, no seed leakage, candidate overflow handling. A synthetic one-step bandit tests optimizer learnability, explicitly not gameplay evidence. Commit each fix before its evaluation.
- Before training, execute all validation seeds with canonical planner and independently replay their complete chosen action/state sequences. Require all entry/intermediate/final hashes to match; inspect state/encoder finite values and action legality.
- Held-out test: planner once plus each learner's initial and validation-selected greedy policy, all 16 fixed test cases. Report all cells, paired clears/HP/potions, decisions/second, latency and censored/errors separately. Independent full-prefix verification of each selected policy's 16 test plans (32 checks). Data generation and inference costs reported separately; battle rollouts are not independent seeds.

## Decision / exit

- Infrastructure passes only with exact reset/replay checks, zero illegal actions/transition errors, finite optimization and honest accounting of every selected case/cap.
- Continue to a larger, separately registered experiment only if **both** learner seeds improve over their own initialization on test (at least two additional clears, or equal clears with median paired terminal-resource score gain >=3 HP-equivalent), and match or beat planner clear count with median paired resource-score loss no worse than 5 HP-equivalent. Resource score is remaining HP on a clear, zero on a defeat; potion counts/types reported separately. A trained policy rescued by validation selecting update 0 is not learning progress.
- An exploratory pass does not promote the live controller or imply generalization across enemies/characters. A failure stops automatic compute escalation; retain evidence and diagnose exploration/data/representation before any further experiment. No unrestricted RL job, hyperparameter sweep or test-set retry.

References: PPO https://arxiv.org/abs/1707.06347 ; invalid action masking https://arxiv.org/abs/2006.14171 .

## Iteration log and commands

1. Implement a 276-feature state encoder and 144-feature dynamic candidate encoder, masked shared actor/critic, complete-episode PPO, strict canonical-prefix reset, frozen seed splits and separate validation-selected test phase. All network weights and raw training traces stay in ignored artifacts. PyTorch is an optional experimental dependency, not imported by the default controller. Initial implementation is committed before synthetic tests or gameplay.
2. Initial synthetic suite at `f2299d4` passed 4/6. The GAE death-return assertion differed by one float32 rounding unit (5.96e-8); use six-decimal tolerance. The synthetic bandit reached 0.7926 probability for its rewarding action after 24 updates, below the test's 0.9 criterion. Preserve that failed observation and extend only this synthetic test to 64 updates, retaining the 0.9 criterion and all optimizer/gameplay budgets. Store framework version metadata as plain strings for safe weights-only checkpoint loading. No game has run yet.
3. At `888b74a`, synthetic suite 6/6 passed. V1 freeze took 42.67 s: 35 ready, five legitimate pre-entry defeats, no trace hash failures. Stop v1 per its gate. V2 recovers first-combat boundaries for all 40 original seeds, keeping the failed preparation data and preregistering the scope change above before any training. No training-derived hyperparameter or test-result changes.
4. V2 bank extraction at `2cb8215` recovered all 40 original first-combat prefixes across seven enemy compositions. Commit the new bank at `cf2a950` before preflight. At that SHA, all eight validation planner episodes and their eight independent full-prefix replays matched exactly; 16 trace triples audited, zero illegal actions. Planner clears 8/8 with mean 79.5 HP; this is an intentionally easier, near-ceiling feasibility baseline. Evidence: `preflight-v1.json`. No PPO training/test outcomes observed yet.
5. Training SHA **`33cb4fb67d8c18dd3937ea9a576a1f50b5d5c250`**, clean tree; PyTorch 2.11.0 / NumPy 2.3.2, CPU one intra/inter-op thread, four engine workers. Each model has **73,794 parameters**. Both completed 12 × 32 = 384 training episodes; 1701 produced 7,043 training transitions, 1702 produced 6,743. Wall times including validation were 175.91 / 176.85 s; collection plus optimization 162.72 / 161.62 s. All 832 training/validation raw trace triples audited, no illegal actions, transition errors, timeouts or action caps. Both runs stopped at the predeclared update cap without extension. Preserve all 26 model/optimizer checkpoints locally with hashes in `training-v1.json`.
6. **Selection frozen before test:** learner 1701 selects update **8**, SHA-256 `522b08a20c2dcb819ba9539f94e0b00c0d556a637b652c4bef0ecbba215868b8`; learner 1702 selects update **4**, SHA-256 `928192599f6cec8058cb51f6359522d32bd81253d14304404afae21d5f374f2d`. Validation checkpoints (update: clears/8, mean clear HP): 1701 `0:6,62.83; 4:8,70.125; 8:8,71; 12:8,70.625`; 1702 `0:8,66.25; 4:8,70; 8:8,70; 12:8,70`. The latter ties select the earlier checkpoint as preregistered. Publish and commit this evidence before opening any learned-policy test outcomes. Validation improvement is not held-out strength evidence.
7. Test SHA **`7d2f266a98bd21d162617f79bd10aa9591e731d8`**. Freeze training results/model selections in that commit, then run all 80 primary test cells and 32 independent selected-plan replays once. Preserve `test-v1.json` unchanged, including its aggregate `pass:false` and `continue_training_gate:false`. No test-driven retraining, model selection or threshold change. Test wall time 57.63 s.
8. Post-test accounting at `b35305c` adds an offline analyzer and optional dependency pins; it changes no policy/optimizer or collected evidence. Recheck all 26 model hashes and 1,000 distinct raw trace/wire/stderr triples across preparation, preflight, training, validation and test: all pass. Six synthetic checks also pass after optional-import handling. Evidence: `analysis-v1.json`. Keep both original failed synthetic checks (`synthetic-v1.json`) and the failed original fixture cohort (`fixtures-v1.json`).

```bash
python3 -m unittest discover -s tests -p "test_ppo.py" -v
python3 scripts/pilot_ppo_e125.py freeze --output artifacts/runs/e125-fixtures-v1.json
python3 scripts/pilot_ppo_e125.py first-combat-bank --source artifacts/runs/e125-fixtures-v1.json --output artifacts/runs/e125-fixtures-v2.json
# Publish and commit the immutable 40-entry fixture bank before preflight/training.
python3 scripts/pilot_ppo_e125.py preflight --output artifacts/runs/e125-preflight-v1.json
python3 scripts/pilot_ppo_e125.py train --preflight artifacts/runs/e125-preflight-v1.json --output artifacts/runs/e125-training-v1.json
python3 scripts/pilot_ppo_e125.py test --training artifacts/runs/e125-training-v1.json --output artifacts/runs/e125-test-v1.json
python3 scripts/analyze_ppo_e125.py --output artifacts/runs/e125-analysis-v1.json
```

## Held-out results and exit decision

| Policy | Clears | Defeats | Censored | Mean HP among clears | Median paired HP versus planner |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing legacy/early-potion planner | 16 | 0 | 0 | 79.750 | 0 |
| Learner 1701, untrained greedy initialization | 5 | 11 | 0 | 70.400 | — |
| Learner 1701, validation-selected PPO update 8 | 16 | 0 | 0 | 73.625 | -6 |
| Learner 1702, untrained greedy initialization | 14 | 1 | 1 | 60.500 | — |
| Learner 1702, validation-selected PPO update 4 | 16 | 0 | 0 | 74.125 | -6 |

These are the **same 16** independent game seeds under paired policies, not 32 independent wins. The two selected policies and planner all finish every case, so their HP comparisons are fully paired. Initial-policy mean HP excludes defeats and caps and is not a like-for-like aggregate strength comparison. Learner 1702's initial policy reaches 120 actions on `test-14` while still nonterminal; its outcome/HP remain unknown. The runner conservatively marks its complete comparison unavailable rather than treating the cap as a death. The original report's aggregate pass flag remains false for this reason. Both selected policies separately pass all 32 canonical-prefix full-trajectory replays, with zero illegal actions or actual transition errors.

| Test case | Planner HP | PPO 1701 HP | PPO 1702 HP |
| --- | ---: | ---: | ---: |
| test-00 | 91 | 83 | 83 |
| test-01 | 75 | 61 | 69 |
| test-02 | 80 | 72 | 72 |
| test-03 | 80 | 75 | 66 |
| test-04 | 80 | 73 | 73 |
| test-05 | 78 | 79 | 79 |
| test-06 | 80 | 72 | 72 |
| test-07 | 80 | 74 | 74 |
| test-08 | 80 | 74 | 74 |
| test-09 | 80 | 79 | 79 |
| test-10 | 74 | 72 | 72 |
| test-11 | 80 | 80 | 80 |
| test-12 | 80 | 74 | 74 |
| test-13 | 80 | 74 | 74 |
| test-14 | 78 | 67 | 74 |
| test-15 | 80 | 69 | 71 |

**Decision:** do not automatically increase training compute, switch the live controller, or proceed to larger-scale RL from this result. Both selected models fail the planner-resource requirement independently of the censored initialization. The pilot establishes that the training/selection/replay pipeline works and that small policies can improve over their own initialization; it does not establish useful superiority to the existing simple planner. Retain the opt-in implementation and reproducible evidence. The next diagnostic is separately proposed as [E126 / #240](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/240), not executed: compare the fixed learned policies against attack-priority and random-action controls on new seeds before claiming context-sensitive planning.

## Behavior, cost and limitations

The planner plays **31 Defends** over its 16 test trajectories; each selected PPO plays only **7**, with 27 Bashes versus the planner's 20. This suggests a stronger attack preference, but the paths diverge, so the counts do not establish that a particular missed block caused a particular HP loss. Stochastic collection with each initial policy already wins 29–30 of 32 episodes in the first batch; a poor untrained greedy initialization can exaggerate apparent improvement. An attack-priority comparison has not yet been run. Training value loss falling near 0.001 is also not proof of foresight when nearly all later training episodes already win.

All three selected/planner arms use six potions across the 16 tests and finish with zero potions in every case. Selected PPO policies make one/two battle-internal card-selection decisions respectively; these branches and their outcomes replay exactly. No learned post-battle card reward, shop, map routing, potion conservation across floors or full-run policy was evaluated. First combat can include legitimately acquired Neow effects/cards/potions; no starter deck, HP or rewards were artificially edited.

Total training: **768 episodes / 13,786 transitions**, 352.75 s including 64 validation episodes. Optimizer work consumes **0.83 / 0.82 s** per learner; most time is real-engine collection/reset, so purchasing GPU compute is not justified by this pilot's timing. Greedy model tensor preparation/forward/selection averages **0.43 / 0.48 ms per decision** on CPU. This metric excludes feature hashing, trace I/O and engine calls; it is not full end-to-end action latency. No model API calls/costs were incurred; Codex development/review token cost is not measured.

The network is a small MLP with structured numerical and hashed entity features, not a complete rules model. Hash collisions and omitted text semantics limit representation; exported observations do not include every hidden RNG variable or complete future draw order. It learns a battle-survival/resource proxy, not whole-run victory probability. All seeds/characters are fixed and these are low-ascension first fights. No arbitrary mid-combat cloning, multiplayer, high-ascension, full-run victory, or general game mastery claim follows.

Optional dependencies are pinned in [requirements.txt](requirements.txt); the default controllers import neither PyTorch nor NumPy. `tests/test_ppo.py` skips explicitly when these optional packages are unavailable. Install only for this experiment, e.g. `python3 -m pip install -r experiments/E125/requirements.txt`. Exact historical game/headless hashes, source patches, Python and framework versions are in each report manifest. Raw states, model/optimizer weights and traces remain under ignored `artifacts/runs/`.
