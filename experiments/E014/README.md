# E014 — Full Jev decisions

Issue #23. Compare raw Jev combat against E011 numerical combat and E012 current-hand beam search, holding the same Jev macro strategy and scene adapters fixed. All three use full-run terminal outcomes, not the first battle. Development: five characters A10 `full_dev_002`, policies hybrid/planned/jev. Held-out: `full_eval_007..009`, five characters A10. $5 / 20000 calls. Promote only if no new errors and wins improve, or explicitly exploratory mean progress if all have zero wins. Headless combat currently excludes potion decisions for all three policies; native allows potions. This is a documented coverage gap, not a claim of native parity.

Iteration 1 is intentionally the existing raw typed Jev instruction; no strength assumption. E013 native traces expose premature end turns despite remaining useful cards, to be measured and addressed in a separate candidate-filter experiment.

Development v1 (f5291ca): 15 normal defeats, no errors. Mean floor hybrid10.6, planned9.8, raw Jev8.4, all 0/5 wins. Total745 requests/$0.106951908. Raw Jev is not a justified default. Proceed with fixed held-out seeds for hybrid/jev; E012 planned is retained as the development diagnostic comparator. No prompt changes before held-out.
