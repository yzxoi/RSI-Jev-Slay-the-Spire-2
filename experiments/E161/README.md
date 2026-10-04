# E161 — factored campaign card selections

Issue: #310. Baseline: E160 complete subset enumeration (4096 limit). Hypothesis:
an O(n) domain and exact subset validation remove combinatorial campaign failures
without changing the set of legal actions. Opt-in only; existing PPO and combat
selection policies retain their frozen action space.

## Frozen protocol, before execution

- Synthetic: exhaustive domains for n=0..8 and every 0<=min<=max<=n; enumerate
  every subset, compare command sets with the complete baseline. Test every one
  of the 8,568 legal 5-of-18 subsets. Reject duplicate, non-integer, missing,
  out-of-domain, wrong-cardinality, stale-state submissions; noncontiguous IDs.
- Real input: E160 A5-001 treatment, run 9c4c8958-5af8-4970-9ebc-7fe483f3354b,
  hashes from committed evaluation-v1.json. Replay ALL recorded command/state
  pairs exactly in an independent engine. At Pael's Tooth select indexes
  [0,1,2,3,4] (five unupgraded Strikes, a compatibility probe, not an optimized
  strategic choice); execute at most 10 deterministic first-legal noncombat
  actions until a living map. Stop before entering combat.
- Independently replay the extended prefix, exact state hashes required.
- Per process 120 seconds including restoration; 15 second RPC; global 300
  seconds. No edited game state, extra seeds, model calls, or native gameplay.
- Gate: synthetic exact equality, all invalid inputs rejected, original prefix
  exact, five cards removed, living map reached, extended prefix exact, clean
  stderr/raw hash audit. Merge as opt-in compatibility only if all pass.
- E160 remains interrupted/error; no resumed full-run win or strength claim.

Reproduction (after implementation commit):
`python3 scripts/validate_subset_e161.py --output experiments/E161/validation-v1.json`

## Iterations

Implementation v1: separate subset domain/resolver; campaign teacher explicitly
opts in and binds selection to fresh state. Existing E160 wire semantics remain
the default. The teacher returns one set, not a numbered combination.
