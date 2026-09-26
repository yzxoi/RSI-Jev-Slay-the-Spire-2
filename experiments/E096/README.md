# E096 — a winning teacher before compression

Issue: [#185](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/185).

Hypothesis: selecting explicit tactical policies by their **actual complete Boss battle outcomes**, rather than the approximate planner score, can discover repeatable wins. This is offline policy search, with rollback cost charged to discovery. It is not a claim that Astra, an action tape, or this policy portfolio is optimal.

The six development fixtures in `fixtures.json` are the two E079 and four E090 selected historical A10 defeats. Four characters, no Defect fixture. Original game v0.111.0 SHA `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`; E093 rebuilt assembly, legacy output mode, full exact entry hash. No injected HP, rewards, draw order, or victory flags. Current Steam adaptation remains #182.

## Preregistered first iteration

Two simple baselines per case: current `retaliate`, with deterministic selection handling, and the same planner with early legal potions. Deterministic selection makes this a new baseline, not an assertion of exact E079/E090 model choice reproduction.

Teacher discovery: 48 combinations of HP-loss price `{0.6,1.5,3.0}`, tactical mode `{balanced,focus_leader,scaling,draw}`, and potion schedule `{early,turn3,turn5,selective}`. These cheap policies generate fresh legal actions using current previews, marginal block, kill pressure, card descriptions/stats and explicit Doom/summon/star utility. The numerical estimates are proposals, **not a substitute engine**. Each candidate plays a complete real-engine battle. Order is fixed. If a case has no win, run three generations of 24 mutations from the four best parents (12 per-turn mode changes, 12 base/potion/selection changes); RNG seed `9600 + case index`. At most 122 runs per case including the baselines. Search ranking: real clear first, then living HP for clears; for defeats minimize last observed leader HP less Doom, then total enemy HP less Doom. This defeat heuristic is not a proof of winnability.

Independent process per branch; four workers; max 300 actions/180 seconds per branch; zero model calls. Stop on a real Boss reward/map boundary with living player, or genuine defeat. In-combat Power Potion card rewards are selections, never counted as Boss clears. Preserve every branch including errors. Raw accepted commands, states, and policy configuration are traced and hashed.

Select the highest-HP successful candidate, rerun its **policy** (not recorded action indices) three times in new processes. Require all three clears and identical action/state trajectory hashes. Record discovery versus execution time separately. Pilot passes with at least three of six repeatable clears, including a non-Ironclad, and all entry/trace hashes valid. Passing allows a separate Jev experiment with a deterministic executor baseline; it does not promote this to full-run play. Failing keeps negative results and stops compression until the teacher improves. Same-entry replay proves determinism only; fresh seeds and full-run evaluation remain necessary.

Commands: `python3 -m unittest discover -s tests -q`; `python3 -m scripts.search_teacher_e096` (commit code first).
