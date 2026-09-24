# E085 — exact-state replay of E084's first reward divergences

Issue: [#162](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/162). Source experiment: [E084 PR #161](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/161), gameplay SHA `4cfb1b661bb900fa7e9861637d0fc404c89171a1`. Baseline after each forced reward: merged `retaliate` policy at `origin/main` SHA `59ab5f2b7c564bf4ea7f1fb9c350f4b88ea35119`.

Hypothesis: in at least some of five selected E084 pairs, the **first differing reward choice alone** reproduces the observed direction of run progression when both continuations use the same baseline policy afterward. These cases were selected after seeing E084 outcomes, so this is a mechanistic diagnostic, not held-out strength or a win-rate estimate. No E084 prompt will be promoted from this result.

Frozen cases: E084 seeds/characters `001` Ironclad, `004` Regent, `001` Defect, `003` Ironclad, `001` Regent. [fixtures.json](fixtures.json) stores each original baseline command prefix, verified source trace/wire hashes, exact pre-reward state hash, and the two observed legal card choices. Original first divergences occurred at decision indexes 25, 81, 16, 37 and 25. The source E084 result and raw traces remain on its closed PR branch/local ignored artifacts; the fixture contains no game state, binary or credential.

Evaluation: replay each prefix from a fresh CLI process with its original seed, verify the exact pre-reward state hash, force one of the two reward actions, then let unchanged `retaliate` + MatchedJev finish the run. Five pairs / ten A10 continuations; two workers, at most 2,000 decisions/300 seconds per continuation; shared at most 2,000 Jev calls/$0.50. Game v0.111.0, sts2-cli `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, Jev `typesafe/jev-1.13-20260917`. Raw traces under ignored `artifacts/runs/`. No HP, reward, RNG or victory edit.

Decision: all ten continuations must reach the frozen entry hash, accept the named legal choice, end normally, and yield verified raw trace SHA-256. Evidence for the single-choice hypothesis needs at least two of five pairs to reproduce the original E084 direction and at most one to reverse it. Otherwise close as negative/inconclusive. A passing replay may justify keeping opt-in replay tooling, never a general reward policy promotion. Record implementation SHA before execution; commit compact results and comment on the PR before merge/close.

## Implementation and exact-state result

The preregistration/freezer (`f93c108`), five frozen prefixes (`f399395`) and opt-in replay evaluator (`a805093d5624474e3f55c3597f7cdd566d5b3206`) were each committed before game execution. `python3 -m unittest discover -s tests -q` passed 114 tests. Exact evaluation command: `python3 -m scripts.evaluate_reward_replay_e085 > artifacts/runs/e085-eval-stdout.log 2>&1`. The source fixture SHA-256 was `f87c27d557ba991e3921c67bc1ca75b180b66d50018a30c36e589148717af74c`. The original game DLL SHA-256 was `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`; the exact headless assembly, patches and dependencies are in [result.json](result.json).

All **10/10** continuations reached their frozen pre-reward state hash, forced the specified legal reward, and ended in normal defeat. All ten raw decision trace hashes verified. No execution error, stall or victory occurred. Both branches used unchanged `retaliate` after the single forced reward.

| Case | E084 original direction | One-choice replay (baseline → treatment) | Direction reproduced? |
| --- | --- | --- | --- |
| Ironclad `001`: Eternal Armor → Mind Blast | worse, floor 17→11 | floor 17→17 | no, tie |
| Regent `004`: Manifest Authority → Solar Strike | worse, Act 2 floor 7→Act 1 floor 17 | Act 2 floor 7→Act 1 floor 17 | yes |
| Defect `001`: Charge Battery → Leap | better, floor 8→11 | floor 8→11 | yes |
| Ironclad `003`: Bludgeon → Headbutt | better, floor 9→11 | floor 11→11 | no, tie |
| Regent `001`: Eternal Armor → Mind Blast | better, floor 6→8 | floor 6→8 | yes |

The preregistered direction rule passed: **3/5 reproduced**, **0/5 reversed**, two tied. The shared Jev budget recorded 110 calls, $0.017613624 provider-reported spend, zero uncertain calls and no matched-request cache hits. No real game was operated; E081 remains paused/unconfirmed. These cases were selected after E084 results, all still ended in defeat, and future decisions/RNG trajectories adapt after each card choice. They show which E084 directions persist when the prompt is removed after the first reward, not an unbiased estimate of a card's general value. In particular, Ironclad `001`'s original floor-11 regression did not reproduce from its first changed card alone.

Decision: **merge the opt-in exact-state replay tool**, since the frozen-entry/legality/execution and direction criteria all passed. Keep the reward policy itself unchanged. The Regent `004` branch is a concrete lead for a separate threat-specific reward experiment; it does not justify reviving E084's generic deck-jobs prompt.
