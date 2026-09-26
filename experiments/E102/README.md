# E102 — Astra turn advice after programmatic safeguards

Issue #196. Preregistered before execution, 2026-09-26.

Two E099 development entries, Ironclad/Silent A10 e093_resources_002 Kin Priest. Four first-pass continuations, one per case/arm. Baseline: unchanged E099 room plan + Jev with E100 potion contracts and E101 exact-engine lethal. Treatment adds **one advisory Astra plan per nontrivial player turn**, <=1200 characters goal+guidance, current state hash/round/run bound. Jev still selects all non-forced cards/targets and handles draws, generated cards and in-combat selections. No hard card sequence, candidate restriction or mid-turn expert rescue is added. Advice persists only within the turn; room boundaries expire it. Deterministic obligations and lethal can finish a turn/room without a needless teacher request. Upstream execution/certificate audits must pass before launch.

Teacher input contains full current state initially, then omits repeated deck/relic text; current hand, powers, intents, resources and recent actions remain. Raw full states are always in traces. Teacher may reason from these known development entries but does not read contemporary baseline outcomes while composing treatment advice. Response packets are committed before execution. This is task-mediated Astra, not an automatic API; token/dollar expense is unknown. Record packets, payload characters (not token estimates), waits, Jev provider cost and branch CPU/time separately.

Budgets: <=240 actions and attempted Jev requests / $0.20 per battle; shared <=$0.80. Baseline <=900 seconds; dynamic <=7200 seconds including task waits, <=30 turn plans and <=1800 seconds per response. Existing transient API retries count conservatively. Four arms start concurrently; no cache, selective reruns or additional rescue. Old game v0.111.0 only; build/model/code hashes recorded.

Decision: all canonical wire/legality/entry, contract, certificate, plan freshness/expiry and trace audits pass. No lost baseline win. If dynamic clears both and uses fewer than E099's 22 response packets, retain as a **development candidate**, not proof of lower Astra tokens/cost. E099 is a historical expert reference, not a contemporary code/cost control. One related seed/two cases and one repeat cannot establish win rate or generalization. Otherwise retain the failure and its mechanism. Merge opt-in tools/evidence only; require disjoint Boss entries and full runs for promotion.

Command: `python3 -m scripts.evaluate_turn_advice_e102 > artifacts/runs/e102.log 2>&1`. Inspect only treatment `turn_request.json` while writing bounded advice; the controller records every actual candidate, Jev response, decision and transition. `python3 -m unittest discover -s tests` validates response freshness/restrictions and existing controller behavior.

## Results

Tested gameplay code **642d2aee2f7854cb13a129bfcba391fd075cb854** (clean tree at launch). 143 unit tests passed before evaluation. All four first-pass continuations completed; no reruns, exclusions, mid-turn expert rescue or unknown-usage calls. [Results](result.json), [canonical audit](audit.json), [turn provenance audit](turn-audit.json), [descriptive trace analysis](analysis.json). These are continuations from Boss entries, not full runs.

| Case / arm | Outcome / final HP | Last player turn | Jev requests / USD | Astra turn packets |
| --- | --- | --- | --- | --- |
| Ironclad / safeguards + static plan | Clear / 43 | 6 | 14 / $0.003249792 | 0 |
| Ironclad / safeguards + turn advice | Clear / 43 | 6 | 13 / $0.003082254 | 6 |
| Silent / safeguards + static plan | Defeat / 0 | 7 | 26 / $0.005903100 | 0 |
| Silent / safeguards + turn advice | Clear / 8 | 9 | 33 / $0.007877268 | 9 |

Contemporary baseline **1/2**, dynamic advice **2/2**, with one additional paired clear and no lost baseline win. All eight contracted potion uses were fulfilled correctly. Three certified lethal actions (one baseline, two dynamic) matched their exact-engine proof's canonical after-state and real Boss-clear boundary. All four entry/prefix, legality, wire/state-chain and cost audits pass. All 15 teacher packets match their committed bytes and current run/state/turn; all 46 treatment model requests received the current turn plan, including the in-combat discard selection. Ordinary candidate choices remained Jev's decisions.

Both arms used `typesafe/jev-1.13-20260917`, old game **v0.111.0**, .NET SDK 9.0.318 and CLI upstream `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`; complete game/DLL/patch hashes are in the result manifests. No claim of compatibility with the current Steam build.

### Cost and latency

Baseline Jev cost: **40 requests / $0.009152892**. Dynamic: **46 / $0.010959522**. Entire E102 pilot: **86 / $0.020112414**. Increased survival can require more Jev decisions; this experiment does not demonstrate cheaper total execution.

Task-mediated Astra received **15 packets**, with **86,348 input and 11,458 output JSON characters**. These are bridge payload sizes, not actual Codex context tokens or billed usage. The historical E099 full-takeover reference used 22 packets, 265,442 input and 8,339 output characters: fewer packets and less input here, but **more output characters**, a different controller, and unmetered teacher reasoning/context. Actual Astra tokens/dollars remain unknown. E099 finished at HP 48/27 versus this pilot's 43/8; neither comparison is a concurrent expert control.

Elapsed baseline continuations were 22.676 s / 34.463 s; dynamic Ironclad 316.758 s and Silent 740.417 s, including 289.214 s / 686.641 s awaiting committed teacher replies. These waits include task orchestration and authoring; they are not API inference latency. Exact-engine lethal proofs cost 5.406–9.241 s each, 20.374 s total across three branches. Proof branches do not count as additional canonical wins.

### What the traces establish

- **Program execution matters independently of advice.** E100 recovered 5/6 clears by executing potion obligations, without extra online teacher calls. E101 separately recovered two paired clears through narrow verified lethal. Here the combined static baseline already clears Ironclad at the same final HP as dynamic advice; six extra teacher packets gave no observed outcome improvement for that case.
- **Fresh guidance can help, but its incremental reliability is unresolved.** Silent moves from defeat to an 8-HP clear in this pair. Earlier potion-only E100 Silent repeats were already 2/3 clears, so this single extra paired success cannot establish a reliable win-rate advantage. The actual E102 teacher followed the changed draw/state rather than prescribing an old seed's action tape.
- **Plain text is not an execution contract.** Dynamic Silent turn 5 played Dodge and Roll and Cloak, then ended with one energy, unused Survivor (11 block) and a free Shiv. HP fell from 59 to 42. Turn 7 played Flechettes and one Defend, then ended with one energy and another Defend (8 block), falling from 29 to 8. Both directly contradict supplied advice. Returned confidence was 0.26 / 0.19; these are observations, not calibrated error probabilities. Potential saved HP from alternatives is arithmetic, not a tested counterfactual battle result.
- **Local adaptation is necessary, and deviations are not uniformly wrong.** Turn 8 Jev chose extra defense and discarded Poisoned Stab despite the advice's attack preference; it survived at 8 HP. Turn 9 a fresh hand offered 29 direct damage against the 26-HP leader. Jev selected the first three attacks and the program certified/executed the final basic Strike. The system handled the changed state without a mid-turn takeover.
- **Unspent energy alone is not an error signal.** Dynamic Silent turn 4 deliberately ends with two energy: 7 carried block plus Plating covers the 8 incoming, and the hand has only ordinary Defends left. The observed transition loses no HP. A blanket no-early-end rule would treat this useful control as a failure.

The compact teacher input omits deck/relic text after the first request. Post-run comparison confirms those fields were unchanged at all 15 request states. Broader use must refresh changed fields rather than assume this fixture property. Current packets remain an experimental task interface, not an automatic general-purpose Astra API or learned router.

### Decision and provenance

The preregistered development gate passes: audited dynamic clears 2/2, preserves the baseline clear, and uses 15 < 22 teacher packets. **Merge opt-in experiment tooling and evidence, not a default every-turn policy.** There is no demonstrated gain from paying for each Ironclad turn, and Silent still nearly loses through execution omissions. The next bounded proposal is [E103 / #198](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/198): verify proposed early end-turns against missed defense, with the covered turn as a negative control. It has not run. Disjoint Boss entries and full-run evaluation remain under #190/#189 before routing or strategy promotion.

Iteration ledger: `06054cb` implements/preregisters the four-arm experiment; `7afb80d` adds freshness/provenance audit; `642d2ae` merges audited upstream E101/E100 evidence and is the exact gameplay SHA. Advice for both cases' turns 1–6 was committed at `a30d3c5`, `b7375a0`, `0c9647a`, `4ecf984`, `549e147`, `edf2248`; Silent turns 7–9 at `a4ae3c3`, `78f9649`, `8e3e572`. Every response was committed before use, with no gameplay-code changes during the pilot. [analysis.json](analysis.json) maps each run/turn/state to its full teacher commit. `9b97a8f` adds only post-run descriptive analysis to expose failures and reconcile payload accounting; it does not alter or relabel tested gameplay.

Read-only reproduction (requires the E102 worktree's ignored raw artifacts):
```bash
python3 -m scripts.audit_boss_trials --experiment E102
python3 -m scripts.audit_turn_advice_e102
python3 -m scripts.summarize_turn_advice_e102
```
Raw canonical and proof traces remain local under `artifacts/runs/`; public results retain hashes, manifests, all outcomes and sanitized teacher packets. A fresh gameplay repetition needs fresh state-bound task replies; committed historical packets cannot silently serve new run IDs.
