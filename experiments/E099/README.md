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

## Results — 2026-09-26

All six first-pass continuations completed normally from identical verified entries. No retries, hidden branch selection or debug mutations. [Machine-readable results](result.json) and [independent raw-wire audit](audit.json) retain every run and hash.

| Mode | Ironclad | Silent | Measured Jev calls / USD | Expert work |
| --- | --- | --- | --- | --- |
| Jev per action | Defeat, turn 8 | Defeat, turn 7 | 40 / $0.009399348 | None during continuation |
| One entry plan + Jev | Defeat, turn 6 | Defeat, turn 6 | 48 / $0.011187414 | Two entry-only plan artifacts; authoring cost unknown |
| Astra persistent room owner | Clear, turn 6, 48 HP (includes Burning Blood) | Clear, turn 9, 27 HP | 0 / $0 Jev | 6 + 16 expert response packets; Astra tokens/USD unknown |
| Fixed shadow composition | Selects Astra: clear | Selects plan: defeat | Reuses the rows above | **1/2 clears; no additional battles** |

The frozen shadow gate loses a clear relative to Astra at every Boss and is **rejected for promotion**. Both teacher continuations clear, so persistent ownership is a useful baseline on these inputs. The data does not establish a cheap total-system solution, and does not measure complete-run strength.

Measured Jev total: **88 requests, $0.020586762, zero unknown-usage attempts**. Requested `typesafe/jev-1.13`, returned `typesafe/jev-1.13-20260917`. Student battles took 21.504–30.316 seconds including prefix replay and ran concurrently. Teacher battles took 158.387 and 346.661 seconds including task/commit wait; these are not API latency measurements. Expert request/response JSON volumes were 265,442 / 8,339 characters, not token counts. The analyst viewed abbreviated current states and still incurred unmetered task context/reasoning. Raw `offline_plan_calls` denotes logical per-case plan artifacts, not measured provider calls. Total Astra expense is unknown.

### What failed, specifically

- Plans changed meaningful decisions: Ironclad made the Bash/Bludgeon leader sequence; Silent used opening poison and concentrated damage. Last live leader HP fell from 129 to 12 for Ironclad and 188 to 56 for Silent. These are trajectory diagnostics, not comparable win probabilities.
- Both plan arms ignored the instruction to spend opening Dexterity Potion and died holding it. Ironclad also died holding Blood Potion. A paragraph in state is not an enforced resource commitment.
- Ironclad plan round 6, state `5d88f1ad36aec0c5a98003bdcf00ecb467d7463661818211827ca406c35251be`: leader 12 HP / 0 block, one energy, legal Strikes preview 16 and 21 damage. Jev chose Defend (4 block), then died. A narrow leader-lethal calculator is a stronger next hypothesis than tuning a confidence threshold. This observation is not a separately executed counterfactual continuation.
- Unguided Jev ended turns with positive energy and playable cards 7 times in each case; plan arms did so 0 / 2 times. These counts are flags, not all proven errors: Astra also intentionally ended one Silent turn with energy because block was sufficient and only redundant defense remained.
- Applying the repository's existing end-turn guard to recorded states blocks **zero** selected end turns. It abstains on unsupported Minion/Plating and later opaque Setup Strike powers. This pilot used unfiltered choices; simply switching the old guard on would not have fixed those recorded boundaries. Current `retaliate` planner strength was not rerun here.
- Both Ironclad student arms played conditional Pact's End without enough exhausted cards; observed enemy HP did not change. Its target damage preview was not a certificate that the conditional effect would occur.
- Teacher is not cost efficient yet. Silent needed 16 packets for nine turns, including generated Shivs, draws and discard choices. Fresh-state validation is necessary, but some local decisions could be delegated under explicit tactical constraints. No such delegated contract was evaluated here.

### Decision and next experiments

Merge **opt-in harness, ownership primitives and evidence only**. Do not change production policy, promote the shadow gate, claim that advice is universally ineffective, or claim lower total cost. E099's unseen-input/full-run routing validation remains open.

Separate atomic follow-ups were opened before testing them:
- [E100 / #192](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/192): execute explicit Astra potion contracts while holding card policy fixed.
- [E101 / #193](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/193): certify one-action leader lethal, abstaining on unsupported effects.

These have **no results yet**. First establish that Jev can honor a plan with computation and execution support; then evaluate bounded turn-level delegation versus full room ownership on disjoint inputs. Learning should retain the conditions, counterexamples and provenance above, not replay these seed-specific teacher packets as a strategy.

## Iteration ledger

- `43e62af`: preregistered fixtures, arms, entry-only plans, shadow gate, budgets and controller; 135 unit tests passed. No game continuation yet.
- `4d3a5f06b52790f047694318303c87afd37d9774`: fixed a wrong existing helper import before game evaluation; CLI import verified. **All six battle manifests pin this tested implementation.** Commands are listed above. SDK/runtime and DLL/assembly/patch hashes are retained per run in `result.json`.
- `7ba7332` through `3bed807`: 22 teacher packets, each committed before its original execution. Each response trace records its exact commit; no packet was revised after seeing its outcome. Four student outcomes were inspected only after both teacher continuations ended. This is dynamic online expert input under one fixed runner, not a hidden implementation change.
- `1252409`: added independent audit and diagnostics after outcomes, no new game actions. All six pass exact entry/prefix, trace/wire hash, current legality, state/wire chain, ownership, committed teacher binding, action counts, terminal boundaries and absence of debug commands.
- `3b4b2e3`: post-run infrastructure hardening: an untracked response file could appear before its commit and make the original bridge fail; wait until immutable committed bytes are available. Atomically replace request snapshots to avoid partial reads. None of the six original runs hit this race. Added a real temporary-Git test for untracked/staged/modified/committed packets; **136 tests pass**. No additional gameplay reruns, so gameplay evidence remains at `4d3a5f0`.

Audit command (read-only on game): `python3 -m scripts.audit_routing_e099`.
Local raw traces: this experiment's worktree under `artifacts/runs/<run_id>/`. They remain ignored and are identified by committed hashes. Teacher packet reproduction is a regression replay, never fresh Astra reasoning.
