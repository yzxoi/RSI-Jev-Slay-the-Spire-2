# E171 — Unseen natural openings, 8 versus 32 branches

Issue #330. Test E169's headroom prospectively with a generic sampler and unchanged E159 FrozenProgram downstream. Historical v0.111.0 certified runtime; no neural/LLM/API calls, edits to game resources, or native-game actions. Follow `.agents/skills/sts2-experiment/SKILL.md`.

## Frozen protocol

64 Ironclad seeds `e171_opening_Ironclad_A{0,5}_{000..031}`, index-major, A0/A5 interleaved. Natural cautious campaign stops before its first potential Gambling Chip opening, at terminal, unsupported selection or budget. Every seed is reported. Independently review effect origin using the entry transition, relic composition and historical game implementation **before any candidate rollout**. Unknown simultaneous selection effects are unsupported. Freeze the first three eligible distinct seeds per difficulty by seed order, never by outcomes. No replacement seeds. Fewer than six roots fails coverage; available roots may still be compared as explicitly incomplete exploratory evidence.

Eight-branch menu: include legacy action, keep all, discard all, and Status/Curse-only, deduplicate, then fill to eight by SHA256(state_hash + canonical_action + `e171`). Canonical action JSON sorts keys, UTF-8, compact separators. Full arm uses every legal subset (at most32), without reusing cached 8-arm results. Rank true clear, living HP, retained potion count; tie fewer discards then lexical indices. Dead HP/inventory contributes zero. Both arms include baseline and keep all; no answer table or semantic card ranking.

Collection <=300s wall, four workers, <=120s/2400actions per seed. Comparison <=900s wall including fidelity checks, four workers, <=120s/300actions per rollout. Execute one root/arm invocation at a time, each with four internal workers, alternating 8/32 order by root. Include prefix restoration, selection, process creation and result persistence in measured invocation latency. No aggregate-time division as a latency estimate. Separately execute the baseline. Freeze selections to disk before fresh execution; independently replay all three chosen paths and freshly execute each search selection. Preserve failures/caps, do not rank incomplete banks.

Deployment gate: all six roots, exact-prefix/fresh-execution/replay fidelity, no lost baseline clear, improvement on at least two distinct seeds, 8-arm retaining every32-arm clear and >=90% of its positive paired living-HP gain (defeat=0), measured 8-arm median<=30s and nearest-rank p95<=60s. Gain denominator0 fails evidence of benefit. Report A0/A5 separately. Small mechanism-conditioned sample is not a full-run win-rate estimate; Astra campaign integration/full-run acceptance remains separate. No default promotion solely from this pilot.

## Reproduction

Implementation is committed before commands below; plan, collection/effect review, and root bank are committed before outcome probes. Record each tested SHA in generated manifests. Raw traces remain ignored under artifacts/runs; published summaries retain hashes.

```sh
python3 -m unittest discover -s tests -p 'test_*opening*.py'
python3 scripts/compare_opening_e171.py plan --output experiments/E171/plan-v1.json
# commit plan
python3 scripts/compare_opening_e171.py collect --plan experiments/E171/plan-v1.json --output artifacts/runs/e171-collection-v1.json
# commit compact collection + independent origin review
python3 scripts/compare_opening_e171.py bank --plan experiments/E171/plan-v1.json --collection experiments/E171/collection-v1.json --review experiments/E171/origin-review-v1.json --output experiments/E171/bank-v1.json
# commit bank
python3 scripts/compare_opening_e171.py evaluate --plan experiments/E171/plan-v1.json --bank experiments/E171/bank-v1.json --output artifacts/runs/e171-evaluation-v1.json
```

Exact commands, code/runtime hashes, measured results and decision will be appended without replacing failed attempts.

## v1 collection: coverage failed, no search comparison performed

Implementation `f80730d`, collection tested `8651445`. Seven synthetic opening tests passed. All64 registered seeds ran within118.656860s (four workers); no replacement seeds, no game edits or model/API calls. All64 raw bundles pass hash audit. This is preservation/integrity of files, not independent transition replay or proof that every engine mechanic is correct.

| Difficulty | Registered seeds | Genuine defeats | Execution errors | Ever reached Act2 / Act3 | Eligible openings |
|---|---:|---:|---:|---:|---:|
| A0 | 32 | 31 | 1 | 7 / 1 | 0 |
| A5 | 32 | 31 | 1 | 8 / 0 | 0 |

No full-run wins, stalls or budget caps. Both errors (`A0-001`, `A5-025`) hit the already-open Crystal Sphere `Vector2I.get_One()` compatibility gap [#64](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/64). Errors are not deaths and were not retried. These are baseline collection outcomes, not a comparison of search policies or Astra macro strength.

Independent scan of all decision and wire logs found **one visible shop offer, zero acquired Gambling Chips, zero target openings**. A0-027 at Act1 floor15 had305gold and a stocked259gold Gambling Chip; FrozenProgram's fixed macro chose `leave_room`. No changed shop decision was executed. Affordability does not establish that buying it was optimal. The absence of roots is influenced by both encounters and acquisition policy; do not infer a population drop rate or absence of search benefit.

The first `origin-review-v1.json` prose incorrectly said zero sightings while its machine-readable hit list already contained this shop. This wording error was corrected in a new commit, before any probes, by `origin-review-v2.json`. Preserve both versions and `bank-v1.json`; `bank-v2.json` is authoritative. The latter freezes an empty eligible cohort. No hypothetical effect-origin certification is asserted for absent roots.

The evaluator at `f859b3e` consumes `bank-v2.json` and emits `evaluation-v1.json` with deployment gate=false, zero rollouts/replays/fresh executions, and null8/32 latency/gain metrics. Its0.000488s is only empty-bank bookkeeping, **not solver latency**. Fidelity=false means not established because there are no roots, not an observed replay mismatch. We cannot answer which branch budget is stronger or faster on new seeds from this sample.

Actual final commands after correcting the exposure wording:

```sh
python3 scripts/compare_opening_e171.py bank --plan experiments/E171/plan-v1.json --collection experiments/E171/collection-v1.json --review experiments/E171/origin-review-v2.json --output experiments/E171/bank-v2.json
# commit empty bank
python3 scripts/compare_opening_e171.py evaluate --plan experiments/E171/plan-v1.json --bank experiments/E171/bank-v2.json --output artifacts/runs/e171-evaluation-v1.json
```

Decision: close PR331 without merging the unvalidated solver. Keep all implementation/results commits and raw evidence. Do not draw more seeds under this protocol, promote a controller, or reinterpret E169's one known seed as unseen evidence. Stop prioritizing rare-relic budget tuning. A better next comparison should sample natural combat states under the intended Astra campaign policy, with broader first-turn coverage and a separately frozen protocol. An explicitly legal shop-acquisition mechanism experiment would also be possible but would answer a different, conditioned question; none was performed here.
