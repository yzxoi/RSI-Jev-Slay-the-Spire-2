# E124: certified checkpoint search with larger action-tree budgets

Issue: [#236](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/236). Status: protocol and opt-in implementation frozen before execution. E121 validators/evidence merged in #235; no engine changes.

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
```

1. Add opt-in snapshot provenance checks, an intermediate-transition identity hash, larger configurable search caps, first-24 compatibility checks against complete E120 wire evidence, and canonical full-prefix final verification. Original E120 defaults remain 24 simulations/full-prefix restoration. The compatibility references are inspected only **after** each algorithm-generated probe; they never nominate actions. Fixed-input evidence hashing before search is audit overhead, not model inference. The checkpoint index explicitly retains E121's failed performance-promotion status.
