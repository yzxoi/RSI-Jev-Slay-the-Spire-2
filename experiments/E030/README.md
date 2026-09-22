# E030 — Typed block/exhaust trigger accounting

Issue #51. User's latest priority is A0 with Jev and few Astra calls; this supersedes the earlier proposed A10 evaluation difficulty, not evidence standards.

Baseline main77422645 planner treats some conditional block as immediate and omits repeated block/exhaust triggers. Hypothesis: explicitly modeling Rage, Feel No Pain, Second Wind, Juggernaut and Daughter of the Wind makes relevant candidate calculations accurate enough to replace Astra arithmetic. Start with deterministic single-enemy outcomes; multi-target Juggernaut allocation is flagged uncertain and is not assigned as a guaranteed kill.

Frozen native cases: E013 attempt5 s104–107, s162–207 with ordinary attack/block/Rage/SecondWind/FNP/Juggernaut actions. Compare first-action block/damage predictions to the next settled before-state, not transient action-result snapshots. Exclude turn transitions, draws with unknown follow-ups and selections from claims of exact deterministic output; report every exclusion. Controls: no trigger, trigger gain after power install, empty SecondWind hand, own block plus Daughter, FNP exhaust counts, target dies between triggers. Unmodeled effects remain explicit.

Commit implementation before unit/offline audit. Promotion as optional arithmetic requires no false deterministic single-target prediction on declared supported cases; it is not a win-rate claim. If audit passes, preregister/run fresh Ironclad A0 pairs a0_e030_dev_001,002,003 planned vs triggered,4000actions/run,3workers,6000Jev calls/$2. Full policy promotion additionally requires held-out improvement; preserve failures.
