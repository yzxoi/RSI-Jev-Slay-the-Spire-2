# E016 — Potion action coverage

Issue #27. Headless had potion inventory but no potion candidates. Compare guarded Jev against equipped (same policy plus normal potion-use commands). Development five characters A10 full_dev_003; heldout full_eval_013..015 same pair. $5/20000 calls. Require no new errors and improved/nonregressed paired strength before promotion. Preserve held-at-death potion counts, use counts and exact effects. No modified inventory/drop rates.

Audit of upstream adapter found two issues requiring a compatibility patch before evaluation: AnyPlayer self potion left target null, and an unconsumed potion was silently discarded. Map AnyPlayer to the single player's creature, and return an explicit error instead of fabricating consumption. Build only after earlier batches finish, pin resulting assembly/DLL hashes. All policies in this experiment share that same corrected engine.
