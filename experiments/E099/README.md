# E099 — intervention granularity before router complexity

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/190

## Preregistered pilot 01

Hypothesis: one bounded Astra room plan changes actual Jev actions enough to match sustained Astra room ownership on some Boss entries; other entries need persistent ownership. Do not assume teacher superiority. A router must eventually match the strongest simple baseline, Astra at every Boss, at lower total cost.

Inputs: the first Act 1 Boss of the E093 `retaliate` traces for **Ironclad and Silent, seed `e093_resources_002`, A10**, selected in that order with a two-case cap before any E099 continuation. Both are Kin Priest. These historical development inputs are disjoint from E096/E097 but are NOT an untouched holdout. `fixtures.json` freezes accepted start/action prefixes, full entry states, state and source hashes. No HP, deck, RNG or reward edits. Headless game v0.111.0 / dependency versions pinned by each manifest; legacy export mode preserves exact input parity, including real usable potions. Current Steam/native transfer is blocked by #182.

Three arms, one continuation per case (six battles):
1. `jev`: Jev chooses every nontrivial actual legal card, target, potion and in-combat selection. No recipe-bank selection. Only a sole legal action is mechanical.
2. `plan`: identical Jev interface plus the frozen entry-only Astra plan in `plans.json`.
3. `astra`: this active Codex/Astra task owns the entire room, including in-combat selections. It supplies state-hash-bound semantic action packets, up to 8 known actions at a time, re-resolved by the sole CLI writer. New turn, card draw, selection, room change or unresolvable instruction invalidates queued actions, not ownership. Each packet includes a short decision rationale, is committed before execution, and gets its commit SHA in the trace. No downstream arm results are read while composing teacher decisions. No rollback search or best-of retries.

Astra is **task-mediated**, not an automatic inference API. Its API token count and dollar cost are unknown. Count offline plan authoring separately from online expert packets, input/output JSON characters, and elapsed time. Characters are payload volumes, NOT model tokens; visible tool-state compression and developer reasoning are not fully represented. Jev provider usage/cost/latency is recorded exactly where reported. Unknown attempts remain counted with conservative budget reservation. No cheaper-total-system claim is possible here.

Fixed shadow gate, committed before tests: if the Boss has Minions and the deck lacks repeatable poison, route to persistent Astra; otherwise route to an entry plan. It uses no model calls, confidence, seed or trace hash. This is an intentionally crude capability hypothesis, NOT a calibrated learned router. Evaluate its frozen assignment by composing the corresponding paired-arm rows: Ironclad=Astra, Silent=plan. This composition is not an independent seventh/eighth battle, tests no mid-room escalation and does not add sample size.

Budgets/fallback: each battle <=240 executed actions. Jev <=240 attempted requests and $0.20 conservatively accounted, <=900 seconds. Astra <=80 packets and <=7200 seconds overall; each response <=1800 seconds. No extra rescue after exhaustion: record unfinished/error/budget outcome, never count it as defeat or win. Six battles only, no selective reruns. Four student battles run concurrently; their final outcomes are withheld from teacher until its two first-pass continuations end. Stop at actual Boss clear/defeat; rewards and full runs are outside this pilot's horizon.

Decision rule: all entry, legality, terminal and trace audits must pass. Report every case and arm. If teacher cannot clear both cases, do not tune a router as if expert rescue were reliable. If plans match teacher wins with fewer interventions, retain plan mode as a candidate; if teacher gains a clear, retain takeover as a candidate. No production strategy promotion on two related development states. Merge only as opt-in experiment/evidence and tested ownership primitives if valid; otherwise fix compatibility in a separately committed iteration, retain all failed attempts. New gates/memory require disjoint evaluation inputs. No automatic online experience promotion in this pilot.

## Reproduction

```sh
python3 -m unittest discover -s tests
python3 -m scripts.evaluate_routing_e099 --mode students
python3 -m scripts.evaluate_routing_e099 --mode astra --case ironclad
python3 -m scripts.evaluate_routing_e099 --mode astra --case silent
```

Teacher responses live in `experiments/E099/teacher/<case>/<sequence>.json`, not action tapes available to Jev. Reproduction of teacher packets is a regression replay; the original first-pass decisions are the teacher evidence. Raw request/response, engine wire and transitions stay under ignored `artifacts/runs/`; compact results/hashes are committed after evaluation.
