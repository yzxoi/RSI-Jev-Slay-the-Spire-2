# E162 — acquire and reserve potions in one expert decision

Issue #311. E160 current-inventory reservations cannot reserve the potion being
bought in the same decision. Hypothesis: bind a typed rule to the fresh offer,
then activate only after exact inventory delta/payment verification. The engine
inventory is never altered by the policy. Existing ID-wide reservation semantics
are preserved, including duplicate IDs; full slots require a separate explicit
discard action followed by a fresh buy/claim request. No speculative auto-discard.

## Frozen validation

- Synthetic: buy/claim success, failed delivery, wrong payment, wrong ID,
  duplicate copies, shifted indexes, full slots, explicit discard then fresh
  acquisition, stale action/state, normal/elite/Boss/emergency masks.
- Offline: all 31 acquisitions (22 claims, 9 buys) in all four E160 treatment
  wires; verify exact offer/inventory bindings. Validate all 200 historical
  expert responses unchanged with the feature disabled.
- Engine pair: independently restore E160 A0-000 seq30 pre-buy state. Buy the
  same Vulnerable Potion; baseline preserves POWER_POTION until Boss at HP<=.35;
  treatment additionally reserves VULNERABLE_POTION until Boss at HP<=.35.
  Follow the recorded forced exit/map commands to the next battle. Same frozen
  combat executor thereafter; stop at first real clear/defeat, max 300 actions,
  120 seconds including full-prefix restoration, 15 seconds/RPC.
- Independently replay both resulting prefixes, exact state hashes; total
  validation budget 600 seconds. Zero new expert requests. No edited state or
  full-run win-rate claim. This is one known handoff counterfactual.
- Gate: all offline/synthetic checks; both engine prefixes exact; baseline
  matches recorded next-battle boundary; treatment keeps the newly reserved
  potion through normal combat unless the frozen emergency triggers; all
  independently replayed hashes and raw audits pass. Merge opt-in only.

Command: `python3 scripts/validate_acquisition_e162.py --output experiments/E162/validation-v1.json`

## Result and decision

Tested `d86f6b5` (full SHA/runtime versions in validation-v1.json). Seven
synthetic success cases and seven rejection cases passed; all 31 historical
acquisitions and all 200 unchanged expert packets passed. Both independent
engine continuations and their replays passed (four raw bundles, 19.192 seconds).

The baseline reproduced its recorded normal fight exactly: clear at 56 HP,
Vulnerable Potion consumed. The treatment cleared at 53 HP and retained it,
with no emergency release or extra expert request. This is a **3 HP cost to
retain one potion**, not evidence that saving it increases eventual win rate.
Merge #315 as opt-in transaction correctness; the strategic reservation rule
still needs downstream Boss/full-run evaluation. No game inventory edits.
