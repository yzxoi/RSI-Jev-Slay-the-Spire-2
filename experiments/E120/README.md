# E120: real-engine flat Monte Carlo versus UCT battle search

Issue: [#230](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/230). Status: protocol frozen before fixture generation or game evaluation.

## Question and baseline

Can an action-tree search improve real battle outcomes without model calls, and does UCT allocate a small search budget better than flat Monte Carlo? E115 tested six fixed policies, not MCTS, and spent most of its time replaying prefixes. This experiment retains that cost rather than assuming a working combat snapshot API.

The control is the existing `teacher.select` legacy planner (triggers and retaliation enabled, early potions). Both search arms use the same control incumbent, candidate generator, 10% uniformly random legal-action rollout policy, terminal utility, engine and budgets. Flat MC cycles through a shuffled root-action list with balanced counts; UCT expands a game action tree with unvisited edges first and `mean + sqrt(2*log(parent_visits)/edge_visits)`. It expands at most one new edge per simulation, then rolls out. Candidates include cards and targets, potions, end turn and card selections. Selection combinations use the existing 128-candidate cap, which is a documented completeness limit.

Each arm returns its best fully observed terminal continuation, including the control incumbent. This is deterministic **battle-plan search**, not a stochastic win-probability estimator or a conventional visit-count execution policy. Repeated paths are not independent worlds. No heuristic dominance pruning, neural network, Jev, Astra API, visible-game actions, or game-state edits.

## Fixed inputs and execution

- Five characters: Ironclad, Silent, Defect, Regent, Necrobinder; ascension 0.
- Two previously unused game seed strings: `e120_20261001_a`, `e120_20261001_b`. All ten cells remain in the report, including fixture failures, deaths before entry, errors and unstarted work.
- Generate each entry by a legitimate run using the control combat policy and fixed macro policy, preferring a currently available Elite map node. Freeze the **first Elite entry**, or the first Boss if no Elite was reached. Do not filter by control outcomes or manually change HP, cards, potions, rewards or RNG. Fixture generation: at most 700 actions / 90 seconds per case, Act 1 only.
- Freeze and commit entry hashes, complete command prefixes, prior action context and provenance before comparing arms. Raw observations and wire traces stay under ignored `artifacts/runs/`.
- Each case first evaluates control once. Each search arm receives that same certified incumbent, charged one simulation and its measured elapsed time. Maximum **24 total simulations / 120 seconds** including that incumbent, startup, replay and rollout; individual simulation cap 15 seconds / 120 post-entry actions. Report intermediate incumbents at 8 and 24 simulations and actual time/count, with capped cells explicitly identified. No equal-compute claim if caps produce unequal work.
- Two case workers, sequential engine subprocesses within each case. Flat/UCT order alternates by case index. Rollout randomness is independently seeded from case, arm and simulation index; game RNG is never reset or resampled inside a continuation.
- Reconstruct every branch with a fresh process and full legal command prefix. Compare exact exported entry hashes; check every revisited tree node and recorded transition. Fully replay each chosen final plan in an independent process, verifying all action boundaries and terminal outcome. This checks observed reproducibility, not completeness of the exported state or fidelity to the current live game.
- If a case has a replay error, engine error, unexpected boundary or transition mismatch, stop its remaining search and mark it invalid; no retry or loss substitution. Other preselected cases still execute, so compatibility gaps are visible. Time/action caps remain censored probes, not defeats, and do not receive terminal utility.

## Utility, measurements and decision

Battle clear ranks above defeat. For clear plans, score residual `HP + 4 * remaining potion count`, then shorter action length. Potion types and future deck/reward value are **not** modeled. Bounded UCT utility: clear `0.5 + 0.5 * min(1, (HP + 4*potions)/(entry_max_HP + 4*entry_potion_capacity))`; defeat 0. Report HP and potion inventories separately, plus descriptive ranking sensitivity to potion weights 0 and 8. No search retuning from those results.

Record clear/defeat/error/cap counts, paired final HP and resources, unique action paths, root breadth, tree depth, completed rollouts, prefix replay time, simulation time, verification time and exact code/dependency hashes. Counts of probes are not sample sizes; there are only ten correlated exploratory battle cases and two game seed strings. No full-run win-rate claim.

Promotion gate: all ten entries and selected plans valid; search must improve at least three cases over control with no clear-to-defeat regression and median paired resource-score gain at least 3. UCT is preferred over flat only if its paired resource-score median is positive and it has more strict gains than regressions, at comparable completed budgets. Otherwise retain the simpler arm or neither. Correct opt-in measurement infrastructure may merge independently of this strength gate; never silently change the default controller.

## Iteration log

1. Initial implementation: actual per-action UCT expansion/backpropagation, root-balanced MC, full-engine rollout, terminal incumbent retention, independent selected-plan verification, immutable fixtures and raw-evidence hashing. Fresh-engine replay is intentionally retained; checkpoint optimization is a distinct follow-up experiment. Incomplete rollouts have no terminal utility; all defeats tie so early suicide is not preferred. Verification cost is reported separately from the search budget. The shared initial control is charged to both arms, but its path is not inserted as fabricated UCT samples.
2. Implementation SHA `2d89786`: eight synthetic search tests and 15 existing teacher/macro/resource tests passed. Fixture command `python3 scripts/evaluate_battle_search_e120.py freeze --output experiments/E120/fixtures.json` produced 10/10 legitimate entries without errors or state edits. Both seeds' first elite is Bygone Effigy (floor 9 for seed a, floor 7 for seed b). Keep this prespecified bank; encounter diversity is consequently limited to one enemy type and cannot support broad combat-generalization claims. Full prefixes, dependency hashes, initial inventories and fixture trace hashes are in `fixtures.json`. Commit this bank before arm evaluation.

## Commands

```bash
python3 -m unittest discover -s tests -p 'test_mcts.py' -v
python3 scripts/evaluate_battle_search_e120.py freeze --output experiments/E120/fixtures.json
# Commit frozen fixtures before comparison; output must not already exist.
python3 scripts/evaluate_battle_search_e120.py run --output artifacts/runs/e120-v1.json
python3 scripts/evaluate_battle_search_e120.py audit --output artifacts/runs/e120-v1.json
```

Historical engine: `dependencies.json` pins sts2-cli `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, .NET SDK 9.0.318 and game v0.111.0. This experiment does not rebuild or modify the ignored engine checkout. Manifest DLL hashes establish the tested binaries. No paid model requests.
