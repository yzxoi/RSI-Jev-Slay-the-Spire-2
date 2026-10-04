# E164 — bounded campaign transactions and explicit mechanical resource defaults

Issue #312. Hypothesis: merge already visible shop and deck-selection choices,
automatically claim free potions with open slots, and traverse a sole route when
HP>50% and the only alternative is Blood Potion. Preserve all actions and active
potion reservations in all 200 E160 expert requests. This is offline protocol
equivalence, not new policy inference, token billing, or win-rate evidence.

## Frozen protocol before evaluation

Compile historical decisions into <=6-action room transactions. Followup choices
may reference ONLY shop offers or deck cards visible at transaction entry.
Supported selections: smith, shop removal, Sapphire Seed upgrade, Symbiote
transform. Stop after a relic purchase, random-card generation, transform or
upgrade completion, and any room/combat boundary. Revalidate current menus,
expected gold/deck/potion/relic/HP deltas and shop offers after every action;
unexpected changes cancel the queue and require fresh expert guidance.

Compiler uses recorded choices to repack old instructions; it cannot demonstrate
that an expert would have made those choices ahead of time. Generated candidate
packets are an offline compression bound. No later random cards or future state
hashes may be used as entry-visible references. Report input/output JSON chars
separately; they are not measured tokens/USD. Preserve explicit reservation
changes, and do not count lost strategic updates as saved requests.

Fixed inputs: all four E160 treatment traces/200 request-response pairs, exact
committed hashes from E160 evaluation-v1.json. Replay all original wire commands
and state hashes in four fresh official-engine processes, with compiled/automatic
choices independently resolved from each fresh state. No new seed or native play.
Synthetic invalidations: changed price, offer, gold, deck, potion inventory,
context, unsupported generated selection, full slots and <=50% HP route.

Gate: >=30% fewer simulated expert requests, exact commands/states and owned
reservation equivalence for all 200 packets, all invalidation checks, all four
prefix replays, zero stderr/hash failures. <=120 seconds/process; <=600 seconds
total, <=4 workers, 15 seconds/RPC. If it fails, retain the result without relaxing
thresholds. Any new natural-run test gets a separate issue/protocol/PR.

Command: `python3 scripts/validate_transactions_e164.py --output experiments/E164/validation-v1.json`

## Iterations

v1 `0a00aa0`: compilation preserved all 200 action/reservation decisions but
only reduced simulated requests to151 (24.5%). Validation stopped at a synthetic
normal purchase: sold offers lose their description metadata, so comparing the
old description hash after setting stock=false was overly strict. No engine
replays started. All partial per-case outputs are preserved in validation-v1/.

v2 treats an unavailable slot as (index, null, false), while retaining complete
identity/price hashes for every stocked offer. This allows the engine's normal
sold-out serialization without accepting changes to any buyable item. Also reject
boolean/noninteger offer indexes. Same inputs/thresholds/budgets; output v2.

v2 `82e834f`: the price-mutation test targeted slot0 even when that slot was
already sold; this intentionally irrelevant change is now correctly ignored.
The test expectation was wrong, so the harness stopped before engine replay.
v3 mutates the first *stocked* offer's price. No policy or gate changes. Preserve
v2 compiled output and failure; rerun all checks into validation-v3.json.

v3 `9a2f4b8`: 200→138 simulated requests (31%), all action/reservation checks
and 38 synthetic checks pass. All four engine replays failed because the new
harness replaced its current decision with get_map's read-only map response.
v4 verifies that query response separately and preserves the decision state,
matching the existing live episode loop. No transaction policy change. All v3
failed traces and result hashes retained; rerun into validation-v4.json.

## Result and decision

v4 tested `e64c5e6` (full SHA/runtime manifest in validation-v4.json): **gate
passed**. All 200 original expert packets preserve actions and active potion
rules; 138 compiled requests remain (62 saved, 31%). Breakdown:33 transaction
followups,22 open-slot potion claims,7 sole-route choices. Per case remaining
requests41/36/37/24, from56/56/57/31. All four independent engine prefixes match,
38 synthetic guards pass, four raw bundles pass hash/stderr audit,13.054 seconds.

Merge PR317 as optional protocol infrastructure. Do not report the offline
compression bound as a measured new-run expert-call/token reduction. The compiler
knows the historical choices, although all transaction references are verified
visible at entry; live expert planning quality is still untested. New seeds and
independent per-run budgets require the separately registered next experiment.
