# E016 — Potion action coverage

Issue #27. Headless had potion inventory but no potion candidates. Compare guarded Jev against equipped (same policy plus normal potion-use commands). Development five characters A10 full_dev_003; heldout full_eval_013..015 same pair. $5/20000 calls. Require no new errors and improved/nonregressed paired strength before promotion. Preserve held-at-death potion counts, use counts and exact effects. No modified inventory/drop rates.

Audit of upstream adapter found two issues requiring a compatibility patch before evaluation: AnyPlayer self potion left target null, and an unconsumed potion was silently discarded. Map AnyPlayer to the single player's creature, and return an explicit error instead of fabricating consumption. Build only after earlier batches finish, pin resulting assembly/DLL hashes. All policies in this experiment share that same corrected engine.

Development v1 (2c9ef70): all 10 normal defeats, no engine errors, 0 wins. Mean floor guarded 8.0, equipped 6.8 (3 worse, 2 ties). 1020 calls, observed $0.141141 plus $0.002688 reserved for 2 uncertain inference calls. This does not support promotion. Preserve exact traces; heldout remains pending after the independent E018 engine-boundary correction.
