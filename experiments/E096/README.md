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

## Result and decision

Tested code: `cb516058dff5333f08327a67b4ef31f290142a95`. `python3 -m unittest discover -s tests -q` passed 131 tests before evaluation. The first shell redirection failed because the new worktree had no `artifacts/` directory; no engine was launched. After `mkdir -p artifacts/runs`, exact command: `python3 -m scripts.search_teacher_e096 > artifacts/e096-stdout.log 2>&1`. No implementation change or rerun replaced the results.

**444 discovery continuations + 12 independent policy repeats = 456 real Boss continuations.** All ended normally, with zero errors or timeouts. Discovery took 924.623 wall seconds, total 958.118 seconds (four workers). Model API calls and spend were zero; Astra authored/reviewed the code and policies in this task, and that offline reasoning cost is not metered by the game runner. Engine/dependency/patch hashes are in [result.json](result.json).

| Frozen A10 entry | Original planner | Early-potion planner | Selected teacher | Three fresh-process repeats |
| --- | --- | --- | --- | --- |
| Silent, E077 Kin | defeat | defeat | no clear; best last Boss HP 65 | not eligible |
| Ironclad, E077 Kin | defeat | clear, 7 HP | same simple baseline, 7 HP | 3/3, exact trajectories |
| Ironclad, E089 Ceremonial Beast | defeat | clear, 36 HP | scaling / loss price 1.5 / early potions, **54 HP** | 3/3, exact trajectories |
| Silent, E089 Vantom | defeat | defeat | no clear; best last Boss HP 8 | not eligible |
| Regent, E089 Kin | defeat | defeat | draw / loss price 1.5 / early potions, **2 HP** | 3/3, exact trajectories |
| Necrobinder, E089 Kin | defeat | defeat | scaling / loss price 3 / turn-5 potions, **7 HP** | 3/3, exact trajectories |

Each successful policy recomputes legal actions from fresh state; repeats do **not** play stored action indices. All selected policies are constant configurations, with no learned per-turn exceptions. The search improved the observed ceiling from 0/6 (original planner), to 2/6 (simple early potions), to **4/6** entries with certified repeatable wins. These ratios are development-set coverage, not independent win-rate estimates. The two Silent failures remain unresolved.

The entire 456-run audit checks trace and wire hashes, frozen entry hashes, membership of each selected action in fresh candidates, complete action/state trajectory hashes, real Boss boundaries, and absence of debug commands. All seven checks pass for all 456 runs; see [audit.json](audit.json). Reproduce the audit with `python3 -m scripts.audit_teacher_e096` while raw traces are available locally.

Mechanistic observations: the Ceremonial winner installs Feel No Pain on turn 3 instead of turn 7 and upgrades hand cards earlier, but multiple downstream choices change, so the +18 HP is not attributed to one card. Regent retains a narrow 2-HP margin and uses cards generated by actual engine RNG; deterministic replay is not robustness to different draws. Necrobinder's best policy reserves its potions until turn 5, showing that indiscriminate early spending is not a universal rule.

**Decision: merge opt-in teacher discovery/replay tools and evidence; keep the production policy unchanged.** The preregistered gate passes (4 repeatable entries, including two non-Ironclad). This justifies a separate Jev plan-selection/reproduction experiment. It does not justify deployment, a current-Steam compatibility claim, or a full-run victory claim. Before full-run promotion we still need fresh seed validation, upstream reward/deck/path decisions, and the current-game adapter.
