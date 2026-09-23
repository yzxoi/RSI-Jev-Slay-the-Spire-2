# E058 — held-out headless route validation

Issue: [#108](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/108). E057's optional cautious route policy changed four map decisions, all on one development seed. This held-out test evaluates whether the same unmodified rule is encountered and helpful on new seeds. Baseline is `planfixed`; treatment is `planfixed_cautious_route` at main merge `cded43435b18bba62191f3ece9f20736c11097d4`. No policy implementation change is permitted in this experiment.

Fixed seeds: `e058_holdout_001` through `_006`; Ironclad and Silent; A0 and A10; 24 matched pairs / 48 episodes, each at most 1,500 actions or 180 seconds, three workers. Pinned `sts2-cli` commit `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, game expected v0.111.0 and SDK 9.0.318. No Jev/Astra calls. Execute `python3 -m scripts.evaluate_route_e058`, with ignored local headless dependencies set up as in `scripts/setup_headless.py`.

Decision rule fixed before execution: change the default only if all 24 pairs complete normally, ≥6 treatment route overrides occur across ≥3 distinct seeds, better−worse ≥3 pairs overall, and A10 better≥worse. Otherwise retain the optional policy and close this PR as negative or inconclusive. Report all outcomes, errors, raw trace hashes and dependency versions separately from native results. A headless matched cohort cannot estimate visible-game win rate.

## Result and decision

Tested SHA `f0e7b66e6286d5c4ca87baef9c3a03c224fe04bb`; command `python3 -m scripts.evaluate_route_e058` with stdout/stderr captured locally under ignored `artifacts/runs/e058-evaluation.log`. `python3 -m unittest discover -s tests` passed 86/86. The manifest in `result.json` records the pinned headless commit, game/assembly DLL SHA-256, patch hashes and SDK version. All 48 raw decision traces passed SHA-256 recheck, and the 24 policy pairs had identical initial-state hashes. There were no Jev or Astra requests and no model cost.

Every episode ended in normal defeat: **0/48 victories, 0 execution errors/stalls**. All 24 matched pairs tied on `(act, floor)`, including all 12 A10 pairs. Four Unknown-over-Monster overrides occurred, in A10 Ironclad/Silent on seeds `_001` and `_006`; no override occurred on the other four seeds. The most advanced held-out result was Silent A0 seed `_002` at Act 3 floor 2 under both policies, still a defeat. `result.json` contains all 48 per-run outcomes, the 24-pair comparison and every trace hash.

The rule fails the preregistered exposure and progress criteria: 4<6 overrides, 2<3 affected seeds, and better−worse=0<3. Close this experiment PR with the negative/inconclusive result. Keep E057's optional headless policy available for research, but do not promote it to the default or assert a win-rate benefit. In this cohort, route rank was rarely exercised and did not change the measured terminal progress when it was; that observation does not establish why those individual runs lost.
