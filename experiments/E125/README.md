# E125: bounded masked-PPO battle-learning pilot

Issue: [#238](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/238). Protocol frozen before evaluation.


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

```bash
python3 -m unittest discover -s tests -p "test_ppo.py" -v
python3 scripts/pilot_ppo_e125.py freeze --output artifacts/runs/e125-fixtures-v1.json
# Publish and commit the immutable 40-entry fixture bank before preflight/training.
python3 scripts/pilot_ppo_e125.py preflight --output artifacts/runs/e125-preflight-v1.json
python3 scripts/pilot_ppo_e125.py train --preflight artifacts/runs/e125-preflight-v1.json --output artifacts/runs/e125-training-v1.json
python3 scripts/pilot_ppo_e125.py test --training artifacts/runs/e125-training-v1.json --output artifacts/runs/e125-test-v1.json
```
