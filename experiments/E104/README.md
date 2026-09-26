# E104 — one cheap Jev recheck on fresh Act-1 seeds

Issue #200. Preregistered before new gameplay, 2026-09-26. Fixed inputs: Ironclad/Silent x e104_unknown_001/e104_unknown_002 x baseline/recheck, A0 single-player. Eight first-pass starts from Neow, not selected Boss entries. No seed search, state edits, action tapes, model-response cache or in-run Astra. Development question: does a cheap discrepancy cue improve actual Act-1 completion when Jev would otherwise end early?

## Identical baseline and treatment environment

Both arms use fresh legal actual-action Jev choices, the existing full-run strategy text, complete model-state observations, and the existing conservative end-turn guard. Both explicitly enable E093 resource mode and validate its observation fields. Combat includes available potions; macro decisions include map/event/rest/shop/card/bundle/selection and potion rewards. Free potion rewards with an open slot are claimed automatically in both arms, matching the existing resource baseline; full slots, skips/discards and buying are decisions from current legal choices. Gold/relic rewards are automatically granted by the CLI; this is not full native reward-interface parity. Sole legal choices require no model call. Previous-decision context is retained for macro card selections.

E100 entry-bound potion contracts, E101 engine-lethal overrides and E102 teacher plans are absent in both arms. They were not validated as a full-run policy on these new states; this pilot isolates the new behavioral cue. It is not a direct win-rate comparison against the historical E102 Boss controller. Unsupported macro states, engine timeouts and API failures are reported, never silently skipped.

## One optional reconsideration

First obtain Jev's normal action. Compute and log the same shadow trigger in both arms: combat_play, positive energy, proposed end_turn, and E103's Plating-aware arithmetic predicts positive defensive HP benefit from a supported currently playable basic Defend or Survivor. Compare with the exact **remaining allowed candidates**, so an unavailable defense cannot trigger. No threshold on model confidence.

For treatment only, one additional semantic Jev request at the unchanged state adds a compact conditional preview (incoming, current/end-turn Block, estimated loss and supported card benefits) and asks it to reassess the unfinished defensive objective. Keep identical action IDs/order and every legal candidate, including end_turn. Honor the second response, even end_turn; no further reconsideration at that decision and no forced card. Each subsequent accepted action produces a fresh state. Existing bounded transient transport retries count as API attempts, not extra semantic reconsiderations.

Opaque effects do not become safety guarantees or global guard-whitelist changes. The preview explicitly ignores unmodeled triggers, play penalties, draw/discard changes and future value; it may prompt reconsideration but cannot prohibit or execute actions. Complete state/rules remain available to Jev. A changed choice is not automatically a correct choice.

## Boundaries, budget and launch order

Stop at an authenticated Act-1 Boss-clear reward/map boundary with a living player after entering an Act-1 Boss combat; in-combat potion-generated rewards/card selections are not clears. Do not enter Act 2. Also stop/include genuine defeat, 800 accepted actions, 800 attempted model requests, $0.35 reserved/reported API budget or 900 seconds per trajectory. Shared cap 6,400 attempts / $2.80; at most four independent CLI processes. Model retry/unknown usage is conservatively reserved. First Boss reward boundary is the terminal evidence; subsequent Boss reward choices are outside this Act-1 scope.

Submission order is fixed in inputs.json: seed 001 Ironclad baseline/recheck, Silent recheck/baseline; then seed 002 in the same character/arm order. Four workers take that queue; completion order is not controlled. Every selected run is reported including stalls and pre-Boss losses. No mid-run prompt/code edits, takeover or selective reruns.

Pinned original game v0.111.0 SHA 9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4; CLI/assembly/patch/.NET/code hashes in manifests. Jev typesafe/jev-1.13, returned version and provider-reported usage logged. Actual task authoring/review Astra cost is unknown; zero online Astra calls cannot demonstrate savings against an unmeasured expert baseline.

## Decision rule

Require provenance, start/seed, complete accepted wire/state chains, fresh action/resource candidates, unchanged second-look state/candidates, exactly one second semantic call per eligible treatment decision, and correct stop boundaries. Report all eight Act-1 outcomes, floor/HP, reward/resource actions, triggers, changed choices, repeat ends, extra calls/cost/latency and stalls. At least two extra paired Act-1 clears and no lost baseline clear, with all audits passing, is an exploratory strength signal. Otherwise retain the negative result and do not promote. Any pass still requires more seeds/characters, A10 and complete runs; no complete-game win claim here.

## Execution

Commit implementation before unit checks and gameplay. Commands: `python3 -m unittest discover -s tests -q`; `python3 -m scripts.evaluate_recheck_e104 > artifacts/runs/e104.log 2>&1`; `python3 -m scripts.audit_recheck_e104`. Store raw model input/output and accepted engine transitions locally under ignored artifacts/runs; publish compact evidence and hashes with PR results.

## Iteration 1 — retained compatibility failure

Gameplay SHA **8c63315d10341b88c882b993fb6729b7a3892952**, initial protocol `61c281b`, read-only auditor `60dc73c`. 151 tests passed before launch. All eight fixed starts ran once; [complete first-cohort results](iteration-01/result.json), [audit](iteration-01/audit.json). The data/accounting audit passes; **execution compatibility does not**.

| Character / seed suffix | Baseline | Recheck arm |
| --- | --- | --- |
| Ironclad / 001 | TypeError at floor 2, HP 68 | Same error at floor 2, HP 68 |
| Silent / 001 | Act-1 clear, HP 2 | TypeError at floor 3, HP 66 |
| Ironclad / 002 | Defeat, floor 7 | Defeat, floor 8 |
| Silent / 002 | Defeat, floor 7 | TypeError at floor 3, HP 61 |

Four fresh states expose `player_powers: null`. E103 arithmetic attempted to iterate it when considering an end-turn. These are execution errors, not strategy defeats; 1/4 versus 0/4 is not a valid strength comparison. No semantic rechecks occurred. One first-pass Act-1 clear is retained, not a complete-game victory. Total 674 Jev attempts / **$0.098998956**, no unknown usage. No state changes or gameplay reruns were used to diagnose the TypeError: the recorded failing inputs reproduce the exception directly.

## Iteration 2 amendment — committed before repair evaluation

After preserving the entire first cohort, repair only the nullable power-list input and add regression coverage. Keep the same eight configurations, launch order, policies, prompts, resources and decision rule. Run the entire cohort again rather than selectively replacing the four errors. These are now **seen-seed compatibility-repaired repeats**, not a new holdout. Keep outcomes under `iteration-02/` and never pool versions to estimate win rate.

The **combined E104 budget remains $2.80 / 6,400 attempts**: deduct iteration 1's reported/reserved use before creating the next session budget ($2.701001044 / 5,726 attempts remain). Per-run caps stay unchanged. Label raw outputs separately, require a new output label rather than overwriting an earlier cohort, and retain every second-cohort failure too. No added Astra, changed strategy or partial run continuation. This amendment and first-cohort results precede the code repair and second launch.
