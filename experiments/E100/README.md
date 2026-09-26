# E100 — executable potion obligations

Issue #192. Preregistered 2026-09-26, before any continuation.

Hypothesis: explicit entry-bound potion obligations recover some E099 plan-arm losses. Baseline is **the unchanged E099 plan and actual-action Jev**, not an old cached result. Treatment adds only `contracts.json`: use the uniquely identified Dexterity potion first; Silent then poisons Kin Priest; Ironclad reserves Blood until at least its full 20% max-HP healing is missing, then drinks immediately. Until due, a contracted potion is unavailable to Jev; other card/potion candidates stay unchanged. Commitments are marked fulfilled only after observed inventory removal; ambiguous, missing or illegal due bindings fail visibly. Expiry is the room boundary; card selections preserve the contract. This freezes the full-heal predicate (no speculative emergency override).

Inputs: both immutable E099 entries, Ironclad/Silent, e093_resources_002, A10, Kin Priest, old v0.111.0 engine. Three repeats per arm per case = 12 continuations, not 12 independent seeds. No HP/RNG/reward edits. Sequential order repeat 0..2, Ironclad then Silent; baseline/treatment on even repeats, treatment/baseline on odd. Each run makes fresh API requests; **no response cache**, no selective retries. Model's existing transient-request retry policy remains enabled, counted conservatively. Policy and model sampling variation is retained.

Budgets: <=240 actions, <=240 attempted model requests, <=$0.20 and 900s per continuation; shared <=$1 across all 12. Stop/include any exhaustion; no extra rescue. Pinned DLL SHA checked, full dependency/model/code hashes in manifests. Calls to the optional Astra interface are absent; plan authoring is inherited unmetered work.

Decision: require verified exact entries, legal actions, complete trace/wire chain, valid once-only contract execution, no false action delivery. At least two additional clears in the six paired comparisons and no lost baseline wins is a development signal for disjoint validation. Otherwise report execution success separately from strength. Either result may merge as opt-in evidence; no production strategy promotion from these related inputs. Lethal override, changed card policy and dynamic teacher plans are excluded.

Commands: `python3 -m unittest discover -s tests`; `python3 -m scripts.evaluate_potion_contract_e100`. Raw traces/results stay in ignored `artifacts/runs/`; publish compact audited outcomes afterward.
