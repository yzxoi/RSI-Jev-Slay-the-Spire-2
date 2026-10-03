# E145 — Complete first-act on-policy reward coverage

Issue273. Hypothesis: before increasing PPO gradients, a policy controlling the entire first act must produce genuine positive terminal feedback on multiple independent game seeds. This is a frozen-policy sampling diagnostic, not gradient training or a full-run win-rate evaluation.

Freeze E140 BC1702 (115,778 parameters, phase encoder, exact checkpoint hash from E140/training-v2.json). Use24 new TRAIN seeds `e145_train_Ironclad_A{0,5,10}_{00..07}`. For each: greedy plus4 stochastic categorical trajectories, total120 attempts but24 independent environment seeds. Sample seeds `14500000 + ascension*10000 + index*10 + stream` for stream0..3; temperature1, no top-k/epsilon/forced actions. A separate NumPy generator pertrajectory; store candidates, probabilities, action index, value, network log-prob and actual sampling log-prob. Existing greedy default remains unchanged.

All combat, route, event, shop, card/potion rewards and selections come from the frozen actor and complete legal menu. No planner, lookahead, LLM, setters or state edits. Stop after a real first-act boss encounter, its rewards and live arrival on Act2 map; status `act_clear` is distinct from full-run `victory`. Stop on any unexpected crossing instead of acting beyond boundary. Ordinary full-run API defaults unchanged. Frozen weights are re-hashed after collection.

120 attempts,180s/2400actions each;8workers;900s total including replays. Six predetermined greedy histories (i00/i01 atA0/5/10) independently replay including defeats. Caps/errors are incomplete, not defeats. No retries or seed replacement. Preserve raw traces under ignored artifacts/runs and publish per-case hashes/compact results. Final330acceptance seeds stay unused.

Gate: all120paths terminal at the specified boundary or natural defeat, all6replays exact, allraw hashes pass; each ofA0/A5/A10 has actual over-act success on>=2distinct base seeds (across greedy/stochastic). Passing permits a separately preregistered complete-act PPO curriculum. Failing means do not expand sparse-terminal-reward training; first validate another curriculum/teacher/domain separately. No gradients in this issue.

Synthetic tests: Boss rewards do not count as act clear; legitimate liveAct2map requires priorBoss; invalid crossing errors; full-run default remains unbounded by acts. Stochastic controller reproduces sample streams, stays within masked choices and log-probs match reported probabilities. A frozen positive E139 training history is used only to verify the boundary machinery, not counted among new sampled successes.

Commands after implementation commit: `python3 -m unittest discover -s tests -p test_onpolicy_act.py`; `python3 -m unittest discover -s tests -p test_run_env.py`; `python3 scripts/audit_onpolicy_e145.py --output artifacts/runs/e145-onpolicy-v1.json`.
