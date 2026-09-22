# E014 — Full Jev decisions

Issue #23. Compare raw Jev combat against E011 numerical combat and E012 current-hand beam search, holding the same Jev macro strategy and scene adapters fixed. All three use full-run terminal outcomes, not the first battle. Development: five characters A10 `full_dev_002`, policies hybrid/planned/jev. Held-out: `full_eval_007..009`, five characters A10. $5 / 20000 calls. Promote only if no new errors and wins improve, or explicitly exploratory mean progress if all have zero wins. Headless combat currently excludes potion decisions for all three policies; native allows potions. This is a documented coverage gap, not a claim of native parity.

Iteration 1 is intentionally the existing raw typed Jev instruction; no strength assumption. E013 native traces expose premature end turns despite remaining useful cards, to be measured and addressed in a separate candidate-filter experiment.
