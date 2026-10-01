# E120: real-engine flat Monte Carlo versus UCT battle search

Issue: [#230](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/230). PR: [#231](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/231). Status: completed; opt-in measurement infrastructure selected for merge, **neither search policy promoted to the default controller**. The following protocol was frozen before fixture generation or game evaluation.

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

## Results — 2026-10-01

Tested comparison SHA: **`311164bc1cf4165c624c92280514c2ec49aa52c4`**. Exact command: `python3 scripts/evaluate_battle_search_e120.py run --output artifacts/runs/e120-v1.json`. The ten-case batch completed in **1000.91 seconds** on the local Apple M3 Max, with two case workers. Every arm reached its 24-simulation limit; no wall-time caps, action caps, engine errors, replay-entry mismatches or selected-plan mismatches occurred. The runner made **zero model calls**; this does not measure the Codex development/review conversation's token cost.

| Case | Control | Flat MC | UCT |
| --- | ---: | ---: | ---: |
| Ironclad a | clear, 31 HP | clear, 31 HP | clear, 31 HP |
| Silent a | clear, 44 HP | clear, 44 HP | clear, 44 HP |
| Defect a | clear, 39 HP | clear, 52 HP | clear, 52 HP |
| Regent a | clear, 45 HP | clear, 45 HP | clear, 45 HP |
| Necrobinder a | clear, 9 HP | clear, 9 HP | clear, 26 HP |
| Ironclad b | defeat | defeat | defeat |
| Silent b | clear, 40 HP | clear, 40 HP | clear, 40 HP |
| Defect b | clear, 6 HP | clear, 6 HP | clear, 6 HP |
| Regent b | defeat | **clear, 5 HP** | **clear, 6 HP** |
| Necrobinder b | clear, 3 HP | clear, 8 HP | clear, 8 HP |

These are **fixed battle-entry outcomes**, not full-run victories or an estimate of 80%/90% full-run win rate. All chosen plans ended with zero potions. Seed a supplied one Colorless Potion per character; seed b supplied none. Potion weights 0/4/8 therefore give identical final rankings on this bank, but this does not validate a general potion valuation scheme. Both search arms rescued Regent b; neither rescued Ironclad b.

| Measurement | Control | Flat MC | UCT |
| --- | ---: | ---: | ---: |
| Selected battle plans clearing | 8/10 | 9/10 | 9/10 |
| Strict resource-score gains over control | — | 3/10 | 4/10 |
| Median paired resource-score gain | — | 0 | 0 |
| Mean paired HP gain (defeat = 0 HP) | — | +2.3 | +4.1 |
| Median charged search/rollout seconds | 3.91 | 93.55 | 93.19 |
| Summed probe time spent restoring the prefix | — | 80.61% | 80.55% |
| Maximum explicitly expanded tree depth | — | 1 | 2 in every case |

The control time includes process startup, replay and battle execution; search times include the same control incumbent plus all probes, and exclude final independent verification. Root widths ranged from 6 to 11 actions. Every battle continuation still ran to a real engine boundary: tree depth 2 refers to UCT's explicit action selection before its rollout, **not** a two-action simulation horizon.

At eight charged simulations, both search arms still cleared 8/10 entries and each had mean HP gain +1.3. At 24 they reached the table above. UCT beat flat in 2/10 selected plans and tied 8/10; median paired difference was zero. Algorithms had different fixed rollout RNG seeds and no repetitions across algorithm seeds. Thus the observed +1.8 mean HP advantage over flat is descriptive; it does not isolate the benefit of UCB allocation from sampling variability.

### Trace findings and evidence boundary

- **Defect a:** both search plans ended the battle on round 4 rather than control round 5, leaving 52 instead of 39 HP. Several actions differ, so this is evidence for the complete continuation, not a causal attribution of 13 HP to one card. Sources: control `9a735a73-8941-4c65-994b-878732734a6f`, flat best `252169d8-3afe-48dc-8a9c-c78fc3569f89`, UCT best `f1158d58-4668-4979-bff3-d6d769f5c405`.
- **Necrobinder a:** UCT's best trajectory first played Defend, then Colorless Potion; its subsequent **random rollout** selected card index 2 (Salvo), whereas control selected index 0 (Nostalgia). It ended on round 5 instead of 6 and retained 17 more HP. The decisive alternative selection was outside the two explicitly expanded tree edges. This supports searching alternative continuations, not a claim that UCB itself understood this card interaction.
- **Ironclad b:** every control/search continuation lost. All six root action means were zero in both arms. The current terminal utility gives no information distinguishing different failed trajectories. More informative failure evaluation is an untested follow-up, not a post-hoc change to this batch.
- The search retained the certified control incumbent. Consequently, absence of regressions on this deterministic bank is partly a property of incumbent retention and verified replay; it is not independent evidence of broad strategic competence.

There were **470 distinct control/search continuations** (10 control + 230 flat + 230 UCT), **30 independent selected-plan verifications**, and **10 fixture-generation runs**. Summing the per-arm probe counts gives 480 because the ten shared control incumbents are charged to both arms. Those are not independent seed samples. All 500 post-fixture continuations matched their frozen entry hash; all 30 verification paths and terminal states matched their source plans. An independent audit of all **510** local trace/wire/stderr triples passed. No selection-space truncation was exercised. This demonstrates observed reproducibility on this bank, not universal CLI correctness, coverage of the known chained-selector bug, or parity with current native multiplayer gameplay.

Compact data: [`results.json`](results.json) and [`fixtures.json`](fixtures.json). The results file retains every probe's status, time, path hash and raw trace references, plus the complete original report's SHA-256. It omits only the duplicate fixture records, already committed separately. Raw evidence remains under ignored `artifacts/runs/`. Validation command: `python3 scripts/evaluate_battle_search_e120.py audit --output artifacts/runs/e120-v1.json`.

### Decision and next work

**Strength gate failed for both arms**: each had median paired gain zero rather than the required >=3. **UCT preference gate also failed**: its median paired advantage over flat was zero. Keep the default controller unchanged. Merge the opt-in search/evaluation infrastructure and complete positive/negative evidence because the correctness gate, fresh-plan verification and trace audit passed; do not advertise a generally stronger or faster agent.

The main demonstrated engineering bottleneck is prefix restoration, consuming about four-fifths of probe time. A separately tested faithful checkpoint near room entry should precede much larger search budgets. After reducing that cost, replicate rollout RNG seeds and compare budgets before crediting UCB for an allocation advantage. Failure-value shaping and better generated-card rollouts are separate hypotheses; neither has been validated here. All ten cases involve one elite type at A0 in historical v0.111.0. Broader encounters, higher ascension, rewards/deck construction and full-run evaluation remain necessary.

Atomic follow-up proposals, not executed: [E121 / #232: faithful map checkpoints](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/232), [E122 / #233: allocation versus rollout sampling](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/233), [E123 / #234: informative defeat utility](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/234).

3. Results iteration: record the exact tested SHA, all ten cells, all caps/errors (none), matched budgets, timing, source hashes and decision above. This iteration changes evidence/documentation only; the tested search implementation is unchanged.
