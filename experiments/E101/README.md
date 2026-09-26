# E101 — exact-engine certification of immediate leader lethal

Issue #193. Preregistered 2026-09-26 before testing.

Refinement of the proposal: a damage preview nominates a move; **it never certifies a win**. Support only legal Ironclad/Silent basic Strikes against the sole non-Min ion leader in a Boss room. Require exported single-hit damage >= HP + block. Then start a separate pinned CLI process, replay only the actual accepted start/action prefix, verify the complete current state hash, play exactly that candidate, and require an actual `boss_clear` boundary with positive player HP. Runtime tests at most one nomination per decision; failed/ambiguous/unsupported replay abstains. Before canonical execution recheck candidate legality; canonical after-state must exactly match the proof. Unknown death, retaliation or conditional effects are not guessed away: a numeric nomination cannot pass without real engine terminal confirmation. Other card types abstain. This is CLI-only; not a native safety claim.

Mechanics: `inputs.json` freezes **every before-state from all six E099 traces**, not just the successful witness. Inspect each state; probe every nominated basic Strike. Report state coverage, abstentions, nominations, nonterminal/failed branches and certified outcomes. Offline branch wins are not new first-pass battle wins. Synthetic unit cases for unsupported cards, block, multiple leaders and opaque revive effects are not formal battle outcomes.

Only after exact recovery of witness hash `5d88f1ad36aec0c5a98003bdcf00ecb467d7463661818211827ca406c35251be` and no replay errors: run 12 first-pass continuations, two E099 entries x three repeats x baseline/lethal. Baseline is E099 static-plan Jev **without potion contracts**. Treatment changes only the certified-lethal override; all ordinary card/potion choices and guidance unchanged. No cache, fresh requests, order repeat 0..2 / Ironclad then Silent / baseline first on even repeats and treatment first on odd. <=240 actions and model attempts, $0.20 and 900s per run, shared $1. All failures/exhaustions included, no extra rescue.

Decision: zero false canonical certificates, correct witness recovery and all trace audits required. Compare clears and intervention counts with contemporary baseline. A strength gain is a development signal; no production/generalization claim on repeated historical entries. Even if strength unchanged, a validated opt-in computation tool may merge with the negative evidence. Same old v0.111.0 game hashes as E099/E100; manifests pin exact SHA/dependencies/model output.

Commands:
```
python3 -m unittest discover -s tests
python3 -m scripts.evaluate_lethal_e101 --stage mechanics --source-root /path/to/e099/worktree
python3 -m scripts.evaluate_lethal_e101 --stage battles
```

Raw branches and canonical traces live separately under ignored artifacts/runs. Exact-entry proof time is a real CPU/latency cost and will be reported; it is not free because it uses no LLM.
