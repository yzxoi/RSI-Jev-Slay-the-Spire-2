# E057 — cautious low-HP route, actual headless paired runs

Issue: [#106](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/106). Hypothesis: when HP≤45% and only ordinary route options compete, preferring `Unknown` to `Monster` may preserve more HP than the current fixed-macro map ranking. An Unknown node is not guaranteed safe; this must be tested, not assumed from E051/E054.

Baseline: `planfixed` at `origin/main` merge `419a3a984323bb4e6d569dce7cb38c1819e41716`. Treatment: `planfixed_cautious_route`; the same approximate combat planner and all non-map fixed macro choices, but `Unknown` rank 4 instead of 2 under HP≤45% (baseline `Monster` rank 3). Rest, Treasure and a worthwhile Shop retain their higher ranks. Fixed cohort: seeds `e057_route_001`, `e057_route_002`, `e057_route_003`; Ironclad and Silent; A0 and A10; 12 matched pairs/24 episodes. Pinned `sts2-cli` commit `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, game expected v0.111.0, dotnet SDK 9.0.318. Each episode is capped at 1,500 actions/180 seconds, maximum three workers. No Jev or Astra calls.

Decision rule: publish every pair's victory/act/floor, errors, and actual route overrides. Promote only if all 12 pairs end normally, at least three treatment map choices differ from the baseline choice on that same treatment state, treatment improves at least two more pairs than it worsens, and A10 improves at least as many pairs as it worsens. Otherwise close the PR with the observed evidence. This is a small exploratory headless simulation, not a native win-rate estimate. Raw traces remain in ignored `artifacts/runs`; compact results and trace hashes are tracked.

Commit implementation before evaluation. Preserve every iteration and record exact tested SHA, commands, versions, outcomes and decision here and in the PR comment.

## Fixed-cohort headless result

Tested implementation SHA `7ca1f5eea58a45b5618108ac9205946cc5d18923`. Command: `python3 -m scripts.evaluate_route_e057`, followed by `python3 -m unittest discover -s tests`. The manifest in `result.json` pins `sts2-cli` commit `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, game DLL SHA-256 `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`, headless assembly SHA-256 `675fdcb39662b7e5a9ed0eabcec13096a9cb2eb015ea53f588f5998e05dcaf21`, and SDK 9.0.318. All 24 raw trace files were SHA-256 rechecked against the result. No model was called; Jev/Astra cost $0. Tests passed 86/86.

All 24 episodes ended in normal defeat, with no execution errors or stalls and no victories. Paired progress is `(act:floor)`; the engine resets `floor` between acts, so act is compared first.

| Seed | Character | Ascension | Baseline → treatment | Outcome | Route overrides |
| --- | --- | ---: | --- | --- | ---: |
| `_001` | Ironclad | A0 | 1:8 → 1:12 | better | 1 |
| `_001` | Ironclad | A10 | 1:6 → 1:7 | better | 1 |
| `_001` | Silent | A0 | 1:12 → 1:11 | worse | 1 |
| `_001` | Silent | A10 | 1:6 → 1:7 | better | 1 |
| `_002` | Ironclad | A0 | 1:9 → 1:9 | tie | 0 |
| `_002` | Ironclad | A10 | 1:6 → 1:6 | tie | 0 |
| `_002` | Silent | A0 | 1:17 → 1:17 | tie | 0 |
| `_002` | Silent | A10 | 1:6 → 1:6 | tie | 0 |
| `_003` | Ironclad | A0 | 1:17 → 1:17 | tie | 0 |
| `_003` | Ironclad | A10 | 1:17 → 1:17 | tie | 0 |
| `_003` | Silent | A0 | 2:6 → 2:6 | tie | 0 |
| `_003` | Silent | A10 | 1:9 → 1:9 | tie | 0 |

The preregistered rule is met: 12/12 pairs complete, four treatment map choices differ from baseline at the same treatment state, overall better−worse = 2, and A10 better/worse = 2/0. The four overrides all occur on seed `_001` at 11/80, 28/80, 14/70 and 26/70 HP; the other two seeds never exercise the rule. This concentration sharply limits generalization, and 0/24 victories means no win-rate benefit was observed. Promote **only as an optional headless policy** for held-out testing, without changing the default route behavior. A later preregistered native run is required to test whether this headless signal transfers to the visible controller.
