# E089 — independent held-out replication of E088 threat budget

Issue: [#170](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/170). Baseline: merged `retaliate` at `b22c28ebed9342fa81a0c94109118024fb226d04`.

E088's treatment improved terminal act/floor in 8/20 exploratory A10 pairs and worsened two, but did not add an Act 2 entry, so its PR was closed. This experiment copies the **unchanged** tested E088 controller policy and resource-check module (E088 gameplay SHA `1f362222f02dbebd2ef340d22879f8f953d4dc37`) into a fresh branch from main. Only the evaluator cohort/label/budget differ. It authorizes at most one potion at the first material Act 1 threat, with Jev selecting from legal potion/target candidates and exact inventory verification. No HP, reward, RNG or victory edit. E088's 20 pairs are not included in the held-out decision count.

Fresh, fixed seeds `e089_holdout_001`–`_006`, Ironclad/Silent/Defect/Regent/Necrobinder, Ascension 10: 30 matched pairs / 60 complete-run CLI episodes. Four workers; each episode max 2,000 decisions/300 seconds. Shared Jev budget 6,000 calls/$1.50 with exact-request `MatchedJev`. Game v0.111.0, sts2-cli `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, Jev `typesafe/jev-1.13-20260917`. Command: `python3 -m scripts.evaluate_budget_holdout_e089`. Raw traces and stdout remain ignored; compact results and verified hashes go in `result.json`.

Decision rule: all 60 raw trace hashes verify, 30/30 initial states match, every first differing action is a same-state legal potion use, every use removes exactly one potion, no more than one authorization per combat, and all 60 runs end normally. Exposure: at least 30 treatment uses across at least 20 pairs. Strength: treatment deeper in at least ten pairs, shallower in at most four, no baseline win-to-loss, and at least one additional Act 2 entry. If all gates pass, merge only as an opt-in policy pending broader/native validation; otherwise close. These cohorts cannot estimate a robust win rate.

Implementation/evaluation SHA, exact command, versions, outcomes, limitations and decision will be added after testing.
