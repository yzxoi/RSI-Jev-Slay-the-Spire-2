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

v1 tested `e0362ea5` (full SHA in failure-v1.json): synthetic assertions passed
and the 193-command Pael prefix plus five-card removal reached the map. The
evaluation harness then failed before independent verification (`KeyError:
case` in shared replay). Preserve this partial result; it does not pass the gate.
v2 adds the missing case metadata, with no policy/protocol/sample changes, and
reruns the entire gate into validation-v2.json.

## Result and decision

v2 tested SHA is recorded in validation-v2.json. 165 small domains / 9,727
legal small subsets matched baseline exactly; 10,374 invalid submissions were
rejected; all 8,568 large subsets validated. Pael's 193-command prefix matched,
five cards were removed, and the living map was reached in one new action.
The 194-command independent replay matched every state. The compact selection
domain was 239 serialized bytes (card descriptions remain in the state).
Total validation: 14.080 seconds; two raw bundles hash-audited successfully.
Existing campaign suite: three tests passed.

Merge #314 as opt-in campaign compatibility. This does not change combat/PPO
selection, demonstrate better strategy, complete E160, or verify native MCP.
