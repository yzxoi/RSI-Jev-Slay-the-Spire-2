# E116 — Minimal multi-seed decision benchmark on Jev

Issue: [#222](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/222).
PR: [#225](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/225).
Status: completed exploratory pilot; no promising assistance signal under the preregistered rule. No native game actions.

## Observed result

All 216 requests completed with valid choices; no retries, fallback, stalls or exclusions. Resolved model `typesafe/jev-1.13-20260917`, provider `TypeSafe`. Paid tested SHA: `3381f173fdfa263fa43420b5ee8f2ec18be6568f`. Python 3.14.7 on macOS 26.6.2 arm64; no game/simulator dependency.

| Condition | H=4 | H=8 | H=16 | Total |
| --- | --- | --- | --- | --- |
| Autonomous first choice | 5/12 | 6/12 | 4/12 | **15/36 (41.7%)** |
| Prescribed-route prediction | 6/12 | 7/12 | 6/12 | **19/36 (52.8%)** |
| Exact midpoint assistance | 7/12 | 5/12 | 7/12 | **19/36 (52.8%)** |
| Remote optimum-flipping edit | 6/12 | 5/12 | 5/12 | 16/36 (44.4%) |
| Optimum-preserving sham edit | 6/12 | 8/12 | 7/12 | 21/36 (58.3%) |
| Direct root-value readout | 12/12 | 12/12 | 12/12 | **36/36 (100%)** |

All binary answer labels are balanced, so always-A, always-B and uniform-random expectation are 50%; the exact solver is 100%. Small-sample below-50% observations do not establish systematically worse-than-random behavior.

Midpoint assistance fixes 5 base mistakes and breaks 1 correct choice: net +4/36, **+11.1 percentage points**, seed-cluster bootstrap interval [0.0, 22.2] pp. Gains by horizon are +16.7, -8.3, +25.0 pp. Reliability and readout gates pass, as does improvement at two horizons, but the prespecified >=15 pp aggregate gain gate fails. No extra tuning or model rerun was performed.

Only **4/36** original/flip pairs are both correct; the same 4 also answer the sham correctly. The model changes its selected action in 13/36 flip pairs and 8/36 sham pairs. Raw switching is not the primary score: switching in the wrong direction is still a failure. The 25% both-correct chance reference applies only to independent fair random answers; these paired model answers are correlated, so it is not a universal null model.

The prescribed-route task also fails to show reliable calculation: it answers **A / yes on 31/36 cases**, although true yes/no labels are 18/18 (16 true positives, 15 false positives, 3 true negatives, 2 false negatives). This is a descriptive posthoc observation, not proof of the model's internal heuristic. We do **not** observe the motivating 'can calculate the supplied route, but cannot choose' dissociation.

The clearest measured separation is direct numeric readout versus graph reasoning under this representation. Readout success does not validate arbitrary rule comprehension or isolate search from state tracking. The pilot has a likely floor problem for Jev even at H=4; horizon-response curves here cannot identify an effective planning horizon.

## Cost, trace and audit

- Reported cost **$0.024303888**; 578,664 input and 6,696 output tokens.
- Request loop duration **165.56 s**; per-request latency p50 **0.745 s**, p95 **0.883 s** (includes isolated worker overhead).
- 216/216 request-response pairs reconstruct exactly from fixtures; all scored choices, costs and hashes reconcile. Deterministic fixture regeneration matches. [Audit](audit.json), [manifest](manifest.json), [summary](summary.json), [per-cell results](results.jsonl).
- Raw trace: ignored `artifacts/runs/e116-pilot-v1/trace.jsonl`; SHA-256 `57e7783753e9387062aed7de449742a47dd4b19611a1696c35dbef2fea69abb0`.
- All calls omit explicit hidden-reasoning counters. This is a short typed-answer protocol, **not verified zero internal reasoning**.
- Probability Brier scores (lower is better): choice .2584, prediction .2465, assisted .2586; constant 0.5 probability has .25. The provider's separate `confidence` field is retained verbatim, not interpreted as probability of correctness.
- Bootstrap intervals resample the observed 12 seed clusters. The readout interval degenerates to [1,1] because every observed answer is correct; this is **not** a confidence guarantee of perfect unseen accuracy. Per-horizon samples are only 12 and outcomes across conditions share worlds.

## Decision and next useful test

Preserve the negative result and merge the isolated, audited benchmark as measurement infrastructure; do not promote a Jev strategy or claim that midpoint help has been established as effective. This repository decision is independent of the failed research-signal gate.

Before scaling the benchmark, a separate experiment should add 1/2-step state-tracking items, counterbalanced yes/no option mappings, and equivalent compact-text versus structured-table representations on fresh seeds. That would test whether the current floor reflects task representation/basic tracking, rather than spend on longer graphs that the current configuration already cannot reliably solve. A further model/budget comparison would require its own fixed protocol. No such calls were run here.

## Objective and hypothesis

Measure consequential first choices separately from prescribed-route prediction in small exactly solvable worlds. Test whether externally computed midpoint continuation values improve Jev choices. This instrument is independent of STS2, and does not measure full-run wins, general intelligence, or proven internal serial depth.

This follows the user's request to build a small multi-seed benchmark and run Jev. Related negative model-selection findings remain on [E113 / PR #217](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/217). No live controller or model routing changes.

## Frozen protocol (before any model call)

- Seeds: `e116_20260929_001` through `e116_20260929_012`.
- Horizons: 4, 8, 16 actions; width 8; two legal actions per nonterminal state.
- 36 base worlds; six independently queried conditions each = 216 requests.
- Conditions: base optimal first action; prescribed-route payoff >=4 (A=yes/B=no); optimal first action with exact midpoint continuation values; remote payoff flip; sham payoff edit; direct root-value readout calibration.
- All labels are balanced 6 A / 6 B per horizon and condition. All failures remain in planned accuracy denominators; invalid decisions have no assigned action-value regret.
- Worlds have one root and two disjoint four-state components after commitment. Neutral state IDs are randomly assigned, rows sorted by opaque IDs. Terminal payoffs are a permutation of 0..7. Later transitions branch to two distinct next states within a component.
- Accept worlds with a unique root optimum and at least two consequential decisions after the root on an optimal path. Route sampling is conditional on a balanced true/false answer. Record rejected attempts. These constraints are oracle-only and fixed before Jev testing.
- Flip swaps the best reachable terminal values under the two root choices and must reverse the unique optimum. Sham swaps two terminal values and must preserve the optimum. Both alter two payoff entries, but edit magnitudes and semantic relevance are not matched.
- Exact dynamic programming provides all values. Independent forward reachable-terminal sets check every nonterminal state's value. Tests additionally exhaustively enumerate action strings on small graphs.
- Exact solver, always A/B, expected uniform random and depth-2 search with zero frontier heuristic are instrument baselines. Since rewards appear only at termination and all horizons exceed 2, this shallow search ties and selects A (50% under label balance). It is not a claim that all shallow heuristics fail.

## Model, limits and exit rule

`typesafe/jev-1.13` via OpenRouter `/api/v1/systemone`, typed choice, no visible rationale requested. Log the resolved version, provider, full usage, confidence/probabilities and response time. Accept only this model family and TypeSafe; no provider/model fallback, no automatic retry. Hidden reasoning is **unverified** when usage omits explicit reasoning counters. A short response is not evidence of zero internal reasoning.

At most 216 paid requests, $0.20 spend budget, $0.005 reservation per request, 25-second total HTTP deadline in a killable worker and 20-minute batch deadline. Stop on unknown billing, a bill exceeding the reservation, or three consecutive invalid responses. Remaining cells are reported as unstarted. Credentials are read in process; only a pipe carries them to the HTTP worker. The benchmark has no game dependencies and uses Python's standard library.

Primary metrics: accuracy by condition/horizon; paired assisted-minus-base accuracy; both-correct original/flip and all-correct original/flip/sham; exact root regret; calibration, cost and latency. Confidence intervals resample the 12 seed clusters, retaining all their horizons and conditions. They are descriptive exploratory intervals, not a confirmatory significance test.

Call assistance an **exploratory promising signal** only if API validity >=95%, direct readout accuracy >=90%, overall assistance gain >=15 percentage points, and gains are positive at >=2 of 3 horizons. Otherwise report no such signal and stop. No prompt tuning or extra paid reruns in this iteration. Correct reproducible tooling may merge regardless of model strength; any substantive research claim requires fresh seeds and different graph families.

## Reproduction and iteration log

1. Commit generator, bounded runner, tests and protocol before evaluation.
2. `python3 -m unittest discover -s tests -p 'test_minimal*.py' -v`
3. `python3 scripts/benchmark_minimal_e116.py freeze`
4. Commit `fixtures.json`; the subsequent manifest records the exact tested SHA and fixture hash.
5. `python3 scripts/benchmark_minimal_e116.py run --env-file /absolute/path/to/ignored/.env --output artifacts/runs/e116-pilot-v1 --execute`
6. `python3 scripts/benchmark_minimal_e116.py audit --output artifacts/runs/e116-pilot-v1`

Raw request/response events live under ignored `artifacts/runs/e116-pilot-v1/`. Publish compact rows, summary, manifest and hash audit after checking them; never publish credentials. The fixture bank contains only generated synthetic data and may be public. Bootstrap seed and randomized request order are fixed. No retry/resume can silently overwrite an existing output directory.

### Preflight iteration

- Implementation SHA `9af05ad`: all six world/solver tests passed (including exhaustive routes on horizons 4/8).
- Freeze: 36 accepted worlds in 51 attempts; 7,308 independent forward-value checks passed; all 216 labels balanced by horizon/condition. Fixture file SHA-256: `6e096ca0932004a080fc80563895982fb84ecdedf8c53443d34b02f95c47d069`.
- Inspection confirmed an important limitation before model testing: on longer graphs, most consequential later decisions lie near the end. For H=16 they lie in layers 12–15; intervening branch choices often tie. We retain these fixtures and will not interpret H as number of consequential decisions.
- Before the paid run, harden missing-model failure handling and JSON-stable missing-provider summaries; add mocked billing, failure-stop and total-deadline checks. No paid calls or outcome-driven changes have occurred.
- SHA `c9bf135`: 8/11 tests passed; three runner mock tests errored because the global subprocess mock also intercepted Python's platform probe. Isolate the platform probe in those tests; no generator or paid protocol change. The failed attempt remains in history.
- SHA `3381f17`: all 11 focused tests passed; used for the one paid batch and independent trace audit. The fixture hash and paid prompts were never changed after freezing.

Actual paid command (credential content was never passed on the command line):

```bash
python3 scripts/benchmark_minimal_e116.py run \
  --env-file /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/.env \
  --output artifacts/runs/e116-pilot-v1 --execute
python3 scripts/benchmark_minimal_e116.py audit \
  --output artifacts/runs/e116-pilot-v1
```

[Descriptive trace inspection](descriptive-analysis.json) tabulates the prediction confusion matrix and action switches directly from `results.jsonl`; its illustrations use the fixed first seed at all three horizons rather than selected model failures.

## Interpretation boundaries and related work

The disjoint-component construction prevents root-action ties but may permit connectivity shortcuts. Longer worlds also have longer prompts, and meaningful decision points need not grow with horizon. Prescribed-route and choice questions differ in intrinsic difficulty. Midpoint assistance gives externally computed information; there is no length-matched irrelevant-annotation arm in this first pilot. Confidence is provider-reported and requires calibration. Only one response is sampled per cell. No output-plan, interactive execution, no-op insertion or STS2 strength is measured.

Graph planning is established prior art: [Bachmann & Nagarajan, ICML 2024](https://proceedings.mlr.press/v235/bachmann24a.html). Atomic planning reasoning already has [ACPBench](https://github.com/IBM/ACPBench), and competency decomposition has [Huang et al., 2026](https://arxiv.org/abs/2607.11197). The contribution sought is a reproducible controlled finding, not a new toy-world name.
