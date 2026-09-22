# E002 — Independent controller with complete decision evidence

Issue #3. Hypothesis: a bounded headless loop can choose actions through Jev without Astra forwarding and preserve all inputs, candidates, outputs, transitions, failures and provider usage.

Scope: first natural combat; preamble and card selection use the same fixed mechanical policy. Combat candidates include playable cards/targets and end-turn. Potions and strategic noncombat decisions are outside this initial capability test.

Fixed sample: Ironclad, seed `trace_001`, ascension 10; first-playable and raw Jev. Maximum 100 requests / $0.15 published-price budget. Provider usage is authoritative; unknown usage prevents further calls.

Decision rule: merge if both episodes terminate normally and the Jev trace is complete, with no invalid candidate selection. Tactical quality will be compared separately in E003.

Iteration 1: implement closed candidate choices, bounded process and network calls, append-only traces, source/version manifests and concurrent experiment workers. Add tests for stale-index prevention through fresh candidate construction, unknown-usage stopping and error retention.

```sh
python3 -m unittest discover -s tests -v
python3 -m rsi.run --characters Ironclad --seeds trace_001 --policies first,jev --max-calls 100 --max-usd .15 --output experiments/E002/results-v1.json
```

Results (implementation `4d5fc8c`): 3 runtime tests passed. Both runs completed with identical initial state hashes. Baseline final HP 57 in 33 steps; Jev HP 53 in 20 steps. Jev used 12 requests, 35,166 input tokens, $0.001476972; model P50 0.994s, P95 2.127s. All model calls and state transitions reconciled. Complete sanitized compressed traces are committed.

Decision: merge the trace infrastructure. The Jev sample lost 4 more HP despite fewer actions, so capability success is not a tactical-improvement claim. E003 will use fixed unseen seeds and a stronger numerical baseline.
