## Objective

Issue: [#227](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/227). Status: implementation/protocol committed before validation; no paid results yet.

E118: extend E116 below its observed floor and compare several current model configurations on the same fresh synthetic worlds. The user explicitly authorized short-horizon probes and a small OpenRouter multi-model comparison.

## Fixed protocol before evaluation

- Eight fresh seeds `e118_20260929_001` through `e118_20260929_008`; horizons 1, 2, 4, 8; width 8 with the same disjoint four-state root components and opaque state labels as E116. Minimum consequential later decisions is min(2, H-1), so short tasks are possible without silently treating them as deep planning.
- Per world: optimal root choice, prescribed-route prediction with A=yes/B=no, and the identical semantic prediction with A=no/B=yes. Each mapping has balanced answers; truth and root optimum are independently balanced. Eight direct-value readout controls (one per seed) are queried first. 32 worlds, 104 independent-context requests per configuration, 520 maximum total.
- Models/configurations: Jev `typesafe/jev-1.13` typed choice; GPT-6 Sol `openai/gpt-6-sol` at reasoning none and low; Claude Sonnet 5.5 `anthropic/claude-sonnet-5.5` at low; Gemini 3.8 Flash `google/gemini-3.8-flash` at low. Public model metadata and canonical slugs are saved before calls. Chat models get the same state/question content and a strict binary JSON output schema. No few-shot demonstrations, prompt tuning, or model fallback.
- Pin official providers: TypeSafe, OpenAI, Anthropic, Google AI Studio. Disable fallback; exclude flex/priority endpoint variants where applicable. Record returned model, provider, complete usage including reasoning/cache tokens and exact request/response hashes. Different interfaces and inference budgets mean these are model-configuration comparisons, not a compute-matched leaderboard.
- Chat completion cap 8192 tokens including reasoning; 60-second total response deadline. No reasoning suppression/exclusion is used to pretend that compute is disabled. Sol-none is verified operationally only where an explicit zero reasoning counter is returned; Jev lacking counters remains unverified. Other configurations explicitly use reasoning.
- Fixed per-configuration spending caps sum to $3: Jev $0.20, Sol-none $0.50, Sol-low $0.80, Sonnet-low $1.00, Gemini-low $0.50. Reserve conservative per-call bounds from input bytes plus overhead and full output cap using frozen provider prices. Stop a configuration on unknown billing (retain reservation), over-reservation cost, three consecutive invalid responses, >10% invalid after at least 20 attempts, or a 25-minute deadline. Do not silently omit unstarted cells. Up to five independent workers, one sequential worker per configuration.

## Hypotheses, baselines and decision rule

H1: Jev has measurable competence on 1/2-step state tracking even though E116 H>=4 was near chance. H2: at least one mainstream configuration solves the exact same graph tasks reliably, indicating the E116 floor is not universal across the tested configurations. H3: pairing inverted answer IDs distinguishes semantic correctness from raw A/B preference.

Exact backward values, independent forward reachability and exhaustive routes verify the labels. Baselines are exact execution, constant-A/B and constant-yes/no. Paired mapping correctness requires BOTH responses correct; constant semantic-yes achieves 50% on balanced worlds, whereas constant raw-A achieves 0%. Independent random answers achieve 25%, which is not a universal null.

Report per-horizon root accuracy, prediction accuracy by mapping, both-mappings-correct rate, semantic consistency, yes/label bias, protocol coverage, inference token usage, cost and latency. Bootstrap complete seed clusters; results remain exploratory with only 8 independent seeds. No paired mapping is counted as two independent worlds.

Exploratory usable range: require >=95% protocol validity, >=7/8 readout controls correct, and >=7/8 correct root choices AND >=7/8 both-mappings-correct worlds at a horizon. Report measured counts and only a contiguous passing prefix from H=1; if all tested horizons pass, mark the range right-censored at >=8, not an exact internal planning depth. Model contrast is promising only if a non-Jev configuration passes at H>=4 while Jev does not, and has >=20 pp paired root-accuracy advantage over Jev across H=4/8. Do not tune or expand the paid bank based on outcomes in this iteration.

## Checklist

- [ ] Commit the protocol, oracle, adapters and meaningful tests before validation.
- [ ] Freeze and commit independently verified fixtures and provider metadata before paid calls.
- [ ] Run the fixed batch; retain all failures, costs and raw local traces.
- [ ] Publish sanitized results/audit and PR comment, then decide merge/close.

## Scope and limitations

No game/overlay/controller changes. No equivalent-text representation arm, no new model training and no hidden-architecture inference. Graph length changes prompt length; many long-graph decisions may tie. One sample per model/configuration/item; no pure intelligence score. The measurement code may merge if correct even when hypotheses fail.

Related: E116 #222 / #225. This issue replaces proposal #227 with an executable protocol; the original proposal is preserved in issue history.

## Reproduction and iteration log

```bash
python3 -m unittest discover -s tests -p 'test_shallow_bench.py' -v
python3 scripts/benchmark_shallow_e118.py freeze
# Commit the frozen bank before the following paid command.
python3 scripts/benchmark_shallow_e118.py run \
  --env-file /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/.env \
  --output artifacts/runs/e118-pilot-v1 --execute
python3 scripts/benchmark_shallow_e118.py audit --output artifacts/runs/e118-pilot-v1
```

The existing E116 worktree is reused on a new E118 branch; E116 source/history and raw traces are preserved. The E116 generator/scorer are not modified. Model catalog and provider endpoints were read without paid inference on 2026-09-29; their snapshots are in `model-metadata.json`. OpenRouter documentation confirms that low effort is not equivalent to disabled reasoning and hidden reasoning shares the completion allowance; official OpenAI documentation confirms Sol supports none. All model/provider/request details will be included in the run manifest and raw traces.

The generator additionally requires both true and false terminal predicates to be reachable in each world, then samples a prescribed route conditional on the prebalanced truth label. This removes impossible negative examples at short horizons. Selection is oracle-only, prior to model calls. Short-horizon graphs naturally have fewer consequential later decisions than E116's H>=4 bank.

- Implementation SHA `25805eb`: all 8 E118 tests passed, including exhaustive routes through H=8 and cross-interface payload equivalence.
- Frozen 32 worlds in 48 attempts; 736 independent forward-value checks passed. Each configuration has 104 planned calls. Fixture SHA-256: `f8292e315d92a2013d9cbfdd5a2e5657ae3e5517a59b95bc61dbd88b86c90ada`.

### Iteration 1 — provider access failure, Jev completed

Tested SHA `1da4d7063e5be8d2a6f724d7a12d60925e2fa74d`. The command above finished with 108 attempted requests: Jev 104/104 valid; each of the other four configurations stopped after its first HTTP 403 provider-terms refusal, with 103 cells explicitly unstarted. These are unavailable measurements, not 0% model accuracy. Do not retry denied configurations.

Jev root accuracy at H=1/2/4/8: 8/8, 7/8, 4/8, 3/8. Both prediction mappings correct: 8/8, 5/8, 4/8, 5/8. Readout 8/8. The preregistered passing prefix is H=1. No reasoning counters were supplied; this does not establish zero reasoning. Known reported cost $0.005833296; unresolved reservations from rejected requests $0.305812500. Audit passed all 108 request/response pairs and regenerated the frozen bank. Full sanitized rows, manifests, summary and audit are in `iteration-1/`; raw responses with account identifiers remain local.

The user confirmed this account cannot use those providers and explicitly requested a different set. Next iteration will retain the same frozen bank, reuse all iteration-1 traces without new Jev calls, and test DeepSeek/Qwen/Kimi configurations within the original combined $3 ceiling. Model selection is based on provider access and public capabilities, not paid outcome-based prompt tuning. The Sol none-versus-low contrast is unavailable.

### Iteration 2 protocol — authorized vendor replacement

After the iteration-1 access failures, the user explicitly requested other model families. Keep all old configurations and evidence; do not retry rejected providers. No prompt, seed, scoring rule, request schedule, token cap or deadline changes. Three new configurations, at most 312 new requests, all reasoning effort `low`:

| Configuration | Model / canonical snapshot | Pinned endpoint | Spending cap |
|---|---|---|---:|
| deepseek_low | deepseek/deepseek-v4.1-flash / 20260910 | deepinfra/fp8 | $0.25 |
| qwen_low | qwen/qwen3.8-max-0902 / qwen3.8-max-20260902 | alibaba | $0.95 |
| kimi_low | moonshotai/kimi-k3 / 20260715 | moonshotai/mxfp4 | $1.40 |

Endpoints advertise structured outputs and reasoning effort; frozen public metadata is in `replacement-model-metadata.json`. DeepInfra is selected for DeepSeek because the first-party endpoint does not advertise structured outputs. Qwen input reservation uses $2.50/M including its higher cache-write price; Kimi uses $3/$15 per million prompt/completion tokens. No automatic fallback. Access is unconfirmed until each first control request.

Audited iteration-1 outputs are copied unchanged into the continuation, with original tested SHA per configuration; Jev is not called again. Spend is counted once. New caps sum to $2.60; previous known cost plus retained unknown reservations is $0.311645796, giving a combined conservative ceiling $2.911645796, below the original $3. The runner rejects repeated configurations and any continuation exceeding that ceiling. The original audit remains reproducible using the original configuration snapshots. Compatibility failures remain unavailable measurements.

```bash
python3 -m unittest discover -s tests -p 'test_shallow_bench.py' -v
python3 scripts/benchmark_shallow_e118.py audit --output artifacts/runs/e118-pilot-v1
python3 scripts/benchmark_shallow_e118.py run --execute \
  --configs deepseek_low qwen_low kimi_low \
  --continue-from artifacts/runs/e118-pilot-v1 \
  --env-file /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/.env \
  --output artifacts/runs/e118-pilot-v2
python3 scripts/benchmark_shallow_e118.py audit --output artifacts/runs/e118-pilot-v2
```

### Iteration 3 — complete unstarted cells after isolated transport timeouts

Iteration-2 source SHA `3e6ac695e9352fa244a3dc4674512745942a9ff6`: DeepSeek stopped on request 43 (42 valid), Qwen on request 12 (11 valid), both `total_http_deadline_60s`. Source rows/manifests are preserved in `iteration-2-stopped/`. DeepSeek known cost $0.012154100, unknown reservation $0.004360580; Qwen known cost $0.022500000, unknown reservation $0.065532000. Kimi continues independently under its original protocol and code; the original runner/module files are unchanged.

The single-unknown-bill exit is unnecessarily restrictive for a transport timeout whose maximum charge is still fully reserved. This infrastructure amendment keeps the exact same prompts, 60-second request limit, 8192-token output cap, configurations, seeds and 104-cell denominators. Only send previously unstarted cells: DeepSeek indexes 43–103 (61 requests), Qwen indexes 12–103 (92 requests), at most 153 new calls. Keep both timed-out cells as failed observations; no retry or answer replacement. Freeze this amendment before continuation.

Retain original per-configuration caps and all known/unknown spend, so the combined ceiling stays $2.911645796. A third timeout stops its configuration; original three-consecutive-invalid and >10% invalid after 20 attempts exits remain. Only `total_http_deadline_60s` may continue: HTTP 403, unknown billing from another cause and parameter/provider errors never receive this exception. Maintain the 1500-second cumulative active execution budget, including the original run time. Prior raw trace bytes and scored attempted rows must remain identical. A dedicated audit reconstructs both ledger phases and all request/response pairs.

This amendment follows observed transport failures, not correctness results. It changes completion policy, so both the strict-stop result and the supplemented result will be published. Remaining incomplete configurations are unavailable for a full-range ability comparison.

```bash
python3 -m unittest discover -s tests -p 'test_shallow*.py' -v
python3 scripts/resume_shallow_e118.py run --execute \
  --env-file /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/.env
python3 scripts/resume_shallow_e118.py audit
```
