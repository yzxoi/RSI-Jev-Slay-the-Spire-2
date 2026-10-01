# E124: certified checkpoint search with larger action-tree budgets

Issue: [#236](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/236). PR: [#237](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/237). Status: completed; restoration/search compatibility passed, expanded-budget and UCT-preference gates failed. Retain the opt-in research tool and evidence, with no default policy/budget promotion. E121's failed performance gates remain failed; no engine changes.

## Hypotheses and prerequisites

H1: after E121's complete checkpoint-fidelity gate passes, fast restoration reproduces E120's search trajectories exactly at the original 24-simulation budget. H2: with the same 120-second per-arm ceiling, raising the simulation cap to 64 finds better complete battle plans. This isolates restoration and compute budget; no utility, rollout policy, candidate-space or UCB-constant changes.

**Amendment before any E124 execution:** E121 passed all ten entry cases and all 120 B/C continuation checks, but both speed-promotion gates failed due to latency outliers (paired median speedup 2.737×, Defect-a median 1.495×). Withdraw the initial proposed speed-promotion prerequisite for this bounded **research-only** end-to-end test. Do not relabel E121 as passing, rerun its timing until success, or enable a default accelerator. Require its unchanged fidelity gate and explicit `--allow-unpromoted-checkpoints` for this experimental runner; record the failed performance status in every manifest. The question is now directly whether more useful search is obtained within the deadline despite observed latency variance.

Bind each checkpoint to its unedited file hash, canonical prefix, exported map/entry hashes, validation evidence and exact engine DLL hashes. Any fidelity failure aborts that case; never silently fall back to full-prefix restoration. Slow samples remain in the budget and report.

## Fixed evaluation

- Same ten E120 frozen entries: five characters × `e120_20261001_a/b`, A0, same elite. This is a development/compatibility comparison, not fresh-seed generalization.
- Same control incumbent and exact E120 case/arm RNG identifiers, epsilon=.1 rollout, full legal candidate handling, loss utility=0, clear utility and final certified-incumbent selection.
- Flat MC versus UCT, 64 simulations including the shared control, 120-second wall ceiling per arm, 15 seconds / 120 actions per probe. Two case workers. Alternate arm order by case index as E120 did.
- At every one of the first 24 simulations, compare status, action path, **all before/after state hashes**, and final state to the corresponding recorded E120 probe. Any mismatch prevents proceeding beyond that case's compatibility gate. Do not instruct the engine to follow the old actions: let the unchanged algorithm generate them and verify the result afterward.
- Record incumbents at 8/24/64 simulations and final budget expiry. Independently replay the chosen final plan. Use full-prefix replay for final verification, so a fast-loaded self-consistent error cannot certify itself. Keep all capped/failed/unstarted cells. Check snapshot creation cost separately and show its per-battle amortization; exclude neither startup nor loader latency from probe budgets.

## Decision and exit

Require complete 24-simulation compatibility for both algorithms in all ten cases, zero actual transition errors, and independently matching final plans before retaining the opt-in experimental integration. This is not E121 speed promotion or default deployment. Report actual completed simulations and elapsed times; unequal caps do not become a matched-simulation comparison.

Expanded search is promising if it gains an additional clear over E120's 9/10 or improves at least three paired case outcomes per arm with median resource gain >=3 over that arm's 24-simulation incumbent, without a clear-to-defeat regression. Otherwise retain the cheaper budget; do not keep increasing work automatically. UCT preference still requires a positive paired median over flat at comparable completed budgets and more gains than regressions. No default-policy promotion from this development bank alone.

Preserve all raw traces locally, publish compact complete results, exact code/binary hashes and PR result comments. Zero model API calls, no visible game, no state edits. E122 #233 remains the separate replicated-RNG allocation experiment; E123 #234 remains the separate loss-utility experiment.

## Commands and iteration log

```bash
python3 -m unittest discover -s tests -p 'test_research_restore.py' -v
python3 -m unittest discover -s tests -p 'test_mcts.py' -v
python3 -m unittest discover -s tests -p 'test_checkpoints.py' -v
python3 scripts/evaluate_fast_search_e124.py --allow-unpromoted-checkpoints --output artifacts/runs/e124-v1.json
python3 scripts/analyze_fast_search_e124.py --output artifacts/runs/e124-analysis-v1.json
python3 scripts/evaluate_battle_search_e120.py audit --output artifacts/runs/e124-v1.json
```

1. Add opt-in snapshot provenance checks, an intermediate-transition identity hash, larger configurable search caps, first-24 compatibility checks against complete E120 wire evidence, and canonical full-prefix final verification. Original E120 defaults remain 24 simulations/full-prefix restoration. The compatibility references are inspected only **after** each algorithm-generated probe; they never nominate actions. Fixed-input evidence hashing before search is audit overhead, not model inference. The checkpoint index explicitly retains E121's failed performance-promotion status.
2. Commit **`28b30dd6b4f38e54fe96767673ac0ae482b1eccc`** before the single complete gameplay batch. All 16 focused tests passed (4 research restoration, 8 MCTS, 4 checkpoint helpers). The clean-tree manifest fixes Python 3.13.5, .NET 9.0.318, headless upstream `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, historical game v0.111.0 and all source-patch/binary hashes. No model API calls or visible-game actions. Run time: **1,224.98 s**, two workers, on the local Apple M3 Max / 64 GB host. Preserve the complete unmodified report in [results.json](results.json); its SHA-256 is `3a518a56ce490ef2046dd30d9220e222a178bc1b7e8abec5fb57b2bfd61dc0b4`.
3. After the batch, commit an offline accounting tool as **`512954fbabe7b4f6abee1eb8da259f9fd22057ef`** before executing it. It distinguishes attempts from completed rollouts, recomputes the first-24 speed comparison, checks final verification transition hashes, and reports snapshot amortization. No game/policy changes or rerun. Derived evidence: [analysis.json](analysis.json). Repeat audit: **1,242** unique raw decision/wire/stderr triples passed with no missing/hash-mismatched files. Raw states and snapshots remain local and ignored.

## Results

All ten cases are valid. The first 24 algorithm-generated trajectories per arm match E120 in status, action path, every exported before/after state, and final state: **480 charged comparisons / 470 distinct probes** (the shared control is counted in each arm). All **20** final selected plans independently replay from the canonical full prefix with identical complete trajectories; the accelerator is not used to certify itself. No transition errors, action-cap failures or forced game-over events were observed.

There were **1,222 distinct search attempts**: 648 clears, 562 defeats and 12 incomplete timeouts. Thus **1,210 completed terminal rollouts**, not 1,222 victories or completed simulations. All 12 timeouts were the last attempt in their arm as the 120-second deadline expired (0.42–1.56 s elapsed per censored probe including teardown, not a 15-second stall). The report's `complete` label means the *attempt cap* was reached: Silent-b flat reaches attempt 64 while its final attempt times out, so only 63 rollouts completed. Use probe statuses, not that label, for completion accounting. One arm took 120.19 s including teardown; no sample was removed. Final independent verification adds 76.23 s summed across 20 arms outside the charged search budgets, and is inside the total batch wall time.

| Case | Flat: old 24 → final HP | UCT: old 24 → final HP | Flat completed / attempted | UCT completed / attempted |
| --- | ---: | ---: | ---: | ---: |
| Ironclad-a | 31 → 36 | 31 → 36 | 61 / 62 | 62 / 63 |
| Silent-a | 44 → 44 | 44 → 49 | 50 / 51 | 50 / 51 |
| Defect-a | 52 → 52 | 52 → 52 | 64 / 64 | 64 / 64 |
| Regent-a | 45 → 45 | 45 → 45 | 64 / 64 | 64 / 64 |
| Necrobinder-a | 9 → 26 | 26 → 26 | 58 / 59 | 59 / 60 |
| Ironclad-b | defeat → defeat | defeat → defeat | 60 / 61 | 60 / 61 |
| Silent-b | 40 → 40 | 40 → 40 | 63 / 64 | 62 / 63 |
| Defect-b | 6 → 6 | 6 → 6 | 64 / 64 | 64 / 64 |
| Regent-b | 5 → 23 | 6 → 6 | 64 / 64 | 64 / 64 |
| Necrobinder-b | 8 → 8 | 8 → 20 | 62 / 63 | 61 / 62 |

All selected clear plans end with zero potions, so the resource delta equals HP delta here. Each arm still clears **9/10**, unchanged from E120 search (the unsearched control clears 8/10). Each improves three cases; mean HP gains over its own old 24-probe result are flat **+4.0**, UCT **+2.2**, but both paired medians are **0**. No extra clear and no median resource gain >=3: **both expanded-budget gates fail**. Keeping the baseline incumbent makes non-regression partly mechanical; it is not an independent safety result.

UCT versus flat: two better, one worse, seven ties; mean and median difference both **0**. Completed counts differ in four cases. No UCT preference is justified. Tree depth is still only three explicit actions (two for Silent-a); the remaining battle is completed by the rollout policy. These results do not imply three-turn lookahead.

## Cost and interpretation

| Measure | Flat MC | UCT |
| --- | ---: | ---: |
| E120 median seconds for 24 probes | 93.55 | 93.19 |
| E124 median seconds at the identical 24-probe path | 46.27 | 46.08 |
| Median paired same-24 speedup | 1.958× | 1.933× |
| Final median charged search seconds | 120.01 | 120.01 |
| Median completed rollouts | 62.5 | 62.0 |

Every same-24 comparison is faster (range 1.72–2.20×), with exactly the same paths. These E120/E124 timings are separate historical batches, not randomized simultaneous timing pairs; E121 contains the paired restoration measurements and their failed promotion gates. Typical *restoration alone* was 2.74× faster in E121, which is different from roughly 1.94× end-to-end search throughput here. Restoration still accounts for about **59%** of aggregate probe time, down from E120's about 81%.

The larger-budget quality comparison uses the same **ceiling**, not the same actual elapsed time: old arms stopped after 24 probes at a median ~93 s; the new ones generally use ~120 s. HP improvements combine extra available trajectories with more actual search time. First-24 timings isolate the path-preserving execution improvement; this is not a pure equal-elapsed algorithm-strength comparison.

Checkpoint creation was already performed in E121 and is excluded from this batch. Its measured full prefix + save + entry + teardown cost was median **3.261 s** (2.834–3.578); the save command itself cost median **0.0868 s** (0.0803–0.1119). Conservatively charging a whole snapshot build independently to each arm amortizes to median **0.0518 s per completed rollout**; in fact the experiment shares the existing snapshot across both arms. At an already-reached map boundary, only the save-command time is the incremental capture cost. None of this removes E121's observed fresh-process loader outliers.

The most useful diagnostic is still Ironclad-b: both arms complete 60 losing rollouts including the control, and every UCT root action has mean utility **0**. Search receives no direction toward a less-bad losing trajectory. On Regent-b, flat's improved plan is probe 52, finishing in round 4 with 23 HP instead of round 5 with 5 HP. On Necrobinder-b, UCT's probe 59 finishes in round 4 with 20 HP instead of round 5 with 8 HP. These successful plans still contain randomized rollout actions, so neither improvement establishes that UCB allocation alone caused it.

**Decision:** merge the bounded opt-in research integration, accounting and evidence because all fidelity/independent-verification gates passed; retain the original cheaper/default 24-probe full-prefix setting and do not promote larger budgets or UCT. Stop automatic budget escalation. E123 [#234](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/234) is the concrete next diagnostic for nonzero information on losing branches; E122 [#233](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/233) separates allocation effects from rollout RNG. Both remain unrun. These are ten previously seen A0 entries against **one elite family**, with one algorithm RNG stream per arm: no fresh-seed generalization, full-run victory, high-ascension claim, arbitrary mid-combat cloning or trained policy result.
