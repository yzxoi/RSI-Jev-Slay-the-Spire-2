# E086 — previous-combat brief at A10 card rewards

Issue: [#164](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/164). Baseline: merged `retaliate` at `b22c28ebed9342fa81a0c94109118024fb226d04`.

## Why this experiment

E084's generic deck-job prompt yielded 3 deeper, 2 shallower and 15 tied runs across 20 A10 pairs, with fewer Act 2 entries than baseline. Its exact-state replay in E085 showed that some first reward choices themselves preserved the direction of progression, but they were selected after the fact and do not establish a generally better rule. An audit of E084 baseline raw traces found 6/20 fatal fights on Act 1 floor 6, 6/20 on floors 7–8 elites, 3/20 on floor 9 ordinary fights, 4/20 on the Act 1 Boss, and 1/20 in Act 2. The four Boss defeats include starts at 53, 65, 82 and 73 HP, suggesting that low HP alone is an inadequate reward signal. These are diagnostic counts from a prior exploratory cohort, not new independent evidence.

Hypothesis: a reward prompt tied to the **observed immediately preceding combat** (fight length, net HP loss, remaining HP and known Boss) helps Jev prioritize the next concrete bottleneck better than the generic `STRATEGY` text. The brief asks Jev to compare each offered card on first-two-turn impact, long-fight impact, cost, synergy and skip. It uses simple transparent thresholds for the short priority sentence; these are experimental heuristics, not established game truths. The treatment changes only `card_reward` Jev context. Combat, map, shop, rest, events, candidates, HP, rewards and RNG are unchanged.

Frozen cohort: `e086_brief_001`–`_004`, Ironclad/Silent/Defect/Regent/Necrobinder, Ascension 10; baseline and treatment, 20 matched pairs / 40 complete-run CLI episodes. Four workers; each episode max 2,000 decisions/300 seconds. Shared Jev budget 4,000 calls/$1.00 with exact-request `MatchedJev`. Game v0.111.0, sts2-cli `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, Jev `typesafe/jev-1.13-20260917`. Command: `python3 -m scripts.evaluate_combat_brief_e086`. Raw traces stay ignored under `artifacts/runs/`; compact results and hashes go in `result.json`.

Decision rule: all 40 trace hashes verify, 20/20 initial-state parity, all 40 episodes end normally, and every first differing action is a card-reward choice from the same state. At least six pairs must diverge; treatment must go deeper in at least five, shallower in at most two, convert no baseline win to defeat, and add at least one Act 2 entry. A pass supports merging only this opt-in prompt for broader tests; otherwise close as negative/inconclusive. Small samples cannot estimate win rate.

Implementation and evaluation SHA, exact command, versions, all outcomes, limits and decision will be added after testing.
