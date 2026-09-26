# E095 — Independent matched-request concurrency

Issue: [#183](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/183).

E093’s frozen 20-episode smoke cohort recorded one 300.789-second timeout, despite that run spending 86.25 seconds inside its own 103 Jev requests. MatchedJev holds one global lock during the HTTP call, serializing unrelated games. The timeout and traces remain part of E093.

Hypothesis: use one in-flight Future per request hash, retaining exact-request deduplication while allowing independent requests to execute concurrently. No prompts, choices, game policy, budgets or model configuration change. On failure, every waiter receives the failure; remove the pending entry so a later retry is possible.

Baseline: current main MatchedJev. Before evaluation, commit code and tests. Deterministic threaded tests use barriers/events (not flaky timing thresholds) to prove independent overlap, exactly one call for identical concurrent inputs, deep-copied cached metadata and propagated failure/retry behavior. Real-API benchmark: first eight distinct request contexts in the fixed E093 smoke config order, frozen from its recorded model_request entries; append exact duplicates of the first two (10 jobs, eight unique) and execute both legacy global-lock and per-request variants with four workers, pinned Jev typesafe/jev-1.13, at most 30 attempted calls / $0.10. Record source trace/fixture hashes, every status, actual calls/cache hits, model time, batch wall time, tested SHA and raw traces. This benchmark is not gameplay or win-rate evidence.

Merge rule: deterministic concurrency/dedup/failure tests pass; both benchmark arms finish normally with eight noncached choices/two cache hits and no invalid choices, and per-request wall time improves. Otherwise preserve failure and investigate. If merged, E093 integrates this runtime-only change in a separately committed iteration and repeats its fixed cohort using prior exact responses where possible, reporting cached replay timing separately from live API throughput.

## Result and decision

Tested clean SHA `2ea82fd`. `python3 -m unittest discover -s tests -q` passed 121 tests, including independent request overlap, one call for identical requests, waiter failure propagation/retry and metadata isolation. `python3 -m scripts.benchmark_matched_e095` used the frozen eight requests plus two duplicates in each arm, four workers. Serial: 5.971 s; per-request: 1.810 s (3.30× throughput for this small sample). Each arm made eight paid choices and two cache hits; all 20 jobs returned valid choices, all trace hashes verified. Budget: 16 attempts, $0.002069508 provider-reported, 0 unknown-cost calls. The observed model is recorded per response in result.json.

Decision: merge the runtime concurrency fix. It satisfies the frozen correctness and API-throughput gates. No game policy or prompt changed, and this small sequential-order API benchmark is not an end-to-end speed guarantee or strength result. E093 will integrate this commit and retain its previous timeout.
