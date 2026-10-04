# E168 — Potion applicability after reservation release

Issue #323. Hypothesis: release is a permission, not evidence of local usefulness. Preserve E159 combat and macro reservations; independently vary E166 typed Ashwater selection and applicability. Four arms: legacy, typed only, applicability only, combined. No teacher calls, policy training, or engine edits.

Applicability v1: Block Potion waits until the unchanged card planner proposes end_turn, then requires positive visible attack damage after current/end-turn block. Reconsider after every real card transition, without spending the bottle against projected states. Regen Potion requires a current HP deficit. Ashwater and Snecko Oil are held because the executor cannot verify hand-transformation usefulness. Other potions preserve baseline behavior. These are conservative experimental rules, not an optimal strategy or certified model of all powers. Regen deficit does not certify how many healing ticks are realized. Ashwater abstention is independent of selection polarity, so interaction may eliminate the typed factor's effect.

## Frozen inputs and gate

All 15 E160 Boss/act2 entries, all three E165 Boss entries (six distinct source seeds), and every E165 treatment use-potion state. Exact source trace/wire hashes, prefix counts, original boundary hashes and historical reservations in plan-v1.json. Entries are natural unmodified game trajectories; branch continuations are diagnostic counterfactuals, not 72 independent seeds or new full runs.

72 trials (18 x four arms), each independently replayed. <=300 actions/120s per encounter and replay, <=900s total, four workers. Legacy must match all original boundaries exactly; zero illegal actions/reservation violations and all replays/bundles pass. Compare applicability/legacy and combined/typed separately. Local gate: no lost clear or HP regression, plus HP/potion-count Pareto improvement at entries from at least two source seeds. Inventory IDs reported separately; no invented scalar HP-per-bottle exchange rate. A lost clear rejects the candidate. Passing local evidence still needs new-seed testing before deployment.

```sh
python3 -m unittest discover -s tests -p test_potion_applicability.py
python3 -m unittest discover -s tests -p test_ashwater_semantics.py
python3 -m unittest discover -s tests -p test_teacher.py
python3 scripts/validate_potions_e168.py plan --output experiments/E168/plan-v1.json
# commit fixed plan before evaluate
python3 scripts/validate_potions_e168.py evaluate --plan experiments/E168/plan-v1.json --output artifacts/runs/e168-evaluation-v1.json
```

Versions, exact tested SHA, trace hashes and complete outcomes are recorded in result manifests. Failed attempts remain committed. No native game equivalence or broad win-rate claim.
