# E116 — Minimal multi-seed decision benchmark on Jev

Issue: [#222](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/222).
Status: preregistered exploratory pilot; results pending. No native game actions.

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
2. `python3 -m unittest discover -s tests -p 'test_minimal_decision.py' -v`
3. `python3 scripts/benchmark_minimal_e116.py freeze`
4. Commit `fixtures.json`; the subsequent manifest records the exact tested SHA and fixture hash.
5. `python3 scripts/benchmark_minimal_e116.py run --env-file /absolute/path/to/ignored/.env --output artifacts/runs/e116-pilot-v1 --execute`
6. `python3 scripts/benchmark_minimal_e116.py audit --output artifacts/runs/e116-pilot-v1`

Raw request/response events live under ignored `artifacts/runs/e116-pilot-v1/`. Publish compact rows, summary, manifest and hash audit after checking them; never publish credentials. The fixture bank contains only generated synthetic data and may be public. Bootstrap seed and randomized request order are fixed. No retry/resume can silently overwrite an existing output directory.

## Interpretation boundaries and related work

The disjoint-component construction prevents root-action ties but may permit connectivity shortcuts. Longer worlds also have longer prompts, and meaningful decision points need not grow with horizon. Prescribed-route and choice questions differ in intrinsic difficulty. Midpoint assistance gives externally computed information; there is no length-matched irrelevant-annotation arm in this first pilot. Confidence is provider-reported and requires calibration. Only one response is sampled per cell. No output-plan, interactive execution, no-op insertion or STS2 strength is measured.

Graph planning is established prior art: [Bachmann & Nagarajan, ICML 2024](https://proceedings.mlr.press/v235/bachmann24a.html). Atomic planning reasoning already has [ACPBench](https://github.com/IBM/ACPBench), and competency decomposition has [Huang et al., 2026](https://arxiv.org/abs/2607.11197). The contribution sought is a reproducible controlled finding, not a new toy-world name.
