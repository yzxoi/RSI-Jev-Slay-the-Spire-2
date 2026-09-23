# E056 — review projected large HP loss before card commitment

Issue: [#103](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/103). Hypothesis: `--pause-on-danger --danger-hp 20` checks only current HP. A read-only turn-start calculation of visible incoming attack, existing Block and proven direct retained-card self-loss can request Astra review before a large HP drop, with a bounded number of extra pauses.

Baseline: `origin/main` merge `4079e143483389a0d72fd2d8c5ff598167ba6a80`, current HP≤20 before spending energy. Fixed retrospective input set: earliest recorded `before` combat state for every `(run_id, floor, turn)` in E051 `F1GR9R0YXCCC` and E054 `DCEND0WRAPGL`, 78 + 53 = 131 states. These are the two native Ironclad A0 runs already analyzed, not new generated samples. SHA-pinned source segments and compact states are in `frozen-turn-starts.json.gz`. Game v0.111.0, mod v0.15.0, Jev `typesafe/jev-1.13-20260917`. Reproduce freeze with:

```sh
python3 scripts/freeze_danger.py --e051-runs /Users/yzxoi/RSI-Jev-Slay-the-Spire-2-e051/artifacts/runs --e054-runs /Users/yzxoi/RSI-Jev-Slay-the-Spire-2-e054/artifacts/runs --output experiments/E056/frozen-turn-starts.json.gz
```

Decision rule: both E051 floor23 turn6 and floor27 turn4 must be flagged with full energy before their recorded HP drop, no legal action may be removed, and the proposed signal may add at most 12 reviews over the 131 frozen states compared with the existing HP≤20 gate. Count baseline and new review points separately; unsupported projections and no-attack controls must abstain. Synthetic controls cover multi-hit, multiple enemies, an immediate-kill possibility, stale/non-turn-start states, and Beckon only where structured `HpLoss` exists. One fixed replay plus tests; no native actions or model requests in this issue. A retrospective alert does not prove Astra could save either run.

Each implementation and failed evaluation will be committed before its replay, then results and decision committed afterward. This issue changes the review signal only; it does not filter cards or execute game actions.

## Iteration 1

- `217735c`: initial 131-state freeze. `4abbf38`: added native action readiness to the same source states before any policy evaluation; final fixture SHA-256 `397c3df33d7d2fd20b0e215e7ba95fa8779df9dba086b1f157744e90706db3e5`.
- Tested implementation SHA `a88911c669a7c894e8b22fbb7f9c17fcb1a89f88`, `review_projected_loss(..., danger_hp=20, min_loss=12)`. Commands: `python3 -m unittest tests.test_predictive_danger`; `python3 -m scripts.replay_danger --output experiments/E056/replay-v1.json`. Tests passed 6/6. Replay: 131 states, baseline current-HP reviews 9, **14 extra** predicted-loss reviews; both target E051 floor23 turn6 and floor27 turn4 were flagged at HP21/energy3, and nine possible immediate-kill states abstained. This fails the preregistered ≤12 extra-review cap despite catching the target states. Preserve this result; next iteration raises the minimum forecast loss to 14 HP, which should remove the two 12–13 HP alerts while keeping both target turns (16 and 28 visible damage). This threshold adjustment is exploratory on the same trace set, not out-of-sample validation.
