# E100 — executable potion obligations

Issue #192. Preregistered 2026-09-26, before any continuation.

Hypothesis: explicit entry-bound potion obligations recover some E099 plan-arm losses. Baseline is **the unchanged E099 plan and actual-action Jev**, not an old cached result. Treatment adds only `contracts.json`: use the uniquely identified Dexterity potion first; Silent then poisons Kin Priest; Ironclad reserves Blood until at least its full 20% max-HP healing is missing, then drinks immediately. Until due, a contracted potion is unavailable to Jev; other card/potion candidates stay unchanged. Commitments are marked fulfilled only after observed inventory removal; ambiguous, missing or illegal due bindings fail visibly. Expiry is the room boundary; card selections preserve the contract. This freezes the full-heal predicate (no speculative emergency override).

Inputs: both immutable E099 entries, Ironclad/Silent, e093_resources_002, A10, Kin Priest, old v0.111.0 engine. Three repeats per arm per case = 12 continuations, not 12 independent seeds. No HP/RNG/reward edits. Sequential order repeat 0..2, Ironclad then Silent; baseline/treatment on even repeats, treatment/baseline on odd. Each run makes fresh API requests; **no response cache**, no selective retries. Model's existing transient-request retry policy remains enabled, counted conservatively. Policy and model sampling variation is retained.

Budgets: <=240 actions, <=240 attempted model requests, <=$0.20 and 900s per continuation; shared <=$1 across all 12. Stop/include any exhaustion; no extra rescue. Pinned DLL SHA checked, full dependency/model/code hashes in manifests. Calls to the optional Astra interface are absent; plan authoring is inherited unmetered work.

Decision: require verified exact entries, legal actions, complete trace/wire chain, valid once-only contract execution, no false action delivery. At least two additional clears in the six paired comparisons and no lost baseline wins is a development signal for disjoint validation. Otherwise report execution success separately from strength. Either result may merge as opt-in evidence; no production strategy promotion from these related inputs. Lethal override, changed card policy and dynamic teacher plans are excluded.

Commands: `python3 -m unittest discover -s tests`; `python3 -m scripts.evaluate_potion_contract_e100`. Raw traces/results stay in ignored `artifacts/runs/`; publish compact audited outcomes afterward.

## Results

Tested implementation **56020a5**. All 12 first-pass continuations completed; [results](result.json), [audit](audit.json). No errors, unknown-usage calls or exclusions. 139 tests passed before execution.

| Arm | Ironclad (3 repeats) | Silent (3 repeats) | Total clears | Jev calls / USD |
| --- | --- | --- | --- | --- |
| Static plan baseline | 0/3 | 0/3 | 0/6 | 146 / $0.033780810 |
| Executable potion contract | 3/3, HP 21/21/16 | 2/3, HP 3/0/3 | 5/6 | 131 / $0.030153144 |

All 12 contracted potion uses were executed exactly once with fresh indices, correct target/predicate, and confirmed removal. All canonical entry/prefix, action legality, resource contract, raw-wire/state chain, terminal, usage and hash checks pass. The two contract obligations were fulfilled even in the one Silent defeat: compliant execution is not a guaranteed win. Six paired comparisons produced five additional clears and no lost baseline wins, exceeding the preregistered development gate. Aggregate Jev **277 calls / $0.063933954**, no Astra calls during continuation; inherited plan/contract authoring is unmetered. Returned model `typesafe/jev-1.13-20260917` and exact game/dependency hashes are in each manifest. Baseline elapsed times 25.118–43.731 s, treatment 21.215–45.338 s; this is total continuation time including prefix replay, not API latency.

Decision: merge opt-in executable contracts and evidence; allow E102 to use the validated execution primitive. Do not promote a general potion strategy or claim 83% unseen win rate: these are three model repeats on each of only two related historical Boss states. Unchanged guidance plus enforceable execution is enough to recover much of this development sample's deficit. A disjoint-input/full-run evaluation is still necessary.

Iteration ledger: `56020a5` committed implementation and preregistration before all 12 battles; `1c26e50` added read-only independent audit afterward. No strategy/implementation changes or reruns during evaluation. Reproduce evidence audit with `python3 -m scripts.audit_boss_trials --experiment E100`; raw source is the E100 worktree's ignored artifacts/runs. Full traces remain local and hashed. The generic audit also supports later branch proofs but E100 made **zero** lethal probes/actions.
