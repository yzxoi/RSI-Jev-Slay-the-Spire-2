E136 — Complete card-selection menus for PPO, without changing game rules

Problem: E133 v1 S1702 update1 train-113-b5 legitimately reached 19 cards / choose 0..2 (191 legal subsets); inherited Jev macro cap returned128 and strict encoder rejected. Entire batch skipped. Source training-v1.json is committed; no held-out policy evaluation.

Hypothesis: an explicit PPO-only complete menu, with a4096 action resource bound that fails rather than truncates, can run this state while leaving every previously supported observation/action representation unchanged. Keep Jev/live/default macro cap128. Actor scores each candidate independently, so no network width/weight/feature-shape change. Same sampled policy, seed, game, reward, episode budget. Baseline selection heuristics receive the same complete legal menu in this research mode; other decisions unchanged.

Implementation: optional selection cap in macro enumeration; opt-in PPO action-space identifier; complete count checked before enumeration; encode accepts an explicit bound; no exclusion/masking of the failed state. Choices<=128 must be byte-identical to old choices, including skip order/IDs. Model parameters remain73794. Oversized4096 menus fail explicitly, not approximate.

Fixed evaluation: synthetic zero/one/up-to-two/all-subset completeness, exact legacy-menu compatibility, overflow refusal before allocation, network normalization and gradient/padding checks above128. Real frozen train-113-b5 source prefix +18 transitions: use original S1702 update0 checkpoint and exact original sampled seed; require pre-error action/state trajectory exact, full191 choices, legitimate battle terminal, then three independent full-prefix replays with all hashes exact. Audit source/current raw traces. No win-rate claim. <=300s, original30s/120actions episode budget. Do not edit engine/DLLs.

Merge into E133 only if all completeness, legacy-compatibility, real failure-resolution, replay and audit gates pass. Register E133 action-space amendment before resumed training; preserve failed v1. Training/resume retry is a separate experiment.

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/256

## Result and merge decision

Tested SHA `08ee3f1`; 19 focused synthetic tests passed. Fixed original source case retained191 complete choices, original model weights and exact sampled seed. All18 pre-error actions/state transitions matched; the new191-choice decision completed and the unchanged policy reached a legitimate defeat. Three independent full-prefix replays matched all transitions and final outcomes; five source/current raw bundles audited.18.021s; no engine/DLL change. This resolves execution, not a win-rate improvement.

```sh
python3 -m pytest tests/test_ppo_actions.py tests/test_ppo.py tests/test_ppo_bank.py tests/test_ppo_scale.py -q
python3 scripts/validate_ppo_actions_e136.py --output artifacts/runs/e136-validation-v1.json
```

Merge the opt-in complete-menu path into E133 because completeness, unchanged supported menus, parameter count, real regression and replay gates pass. The encoder feature version remains unchanged; the new independent action-space identifier is recorded. Existing/default Jev cap128 is unchanged. Menus above4096 still fail explicitly. Resume recovery remains separately gated by E137.
