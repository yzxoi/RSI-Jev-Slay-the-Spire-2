# E015 — Conservative end-turn guard

Issue #24. Native traces demonstrate wasted energy with useful basic cards. The filter excludes end turn only with a legal, known basic Strike doing HP damage or a basic Defend preventing incoming damage. Unknown powers, Pain, Normality and Ice Cream disable the filter. It does not choose a card, enforce every play, or claim exact future dominance. Jev still decides among cards and potions. Development: five characters A10 full_dev_002, compare jev/guarded. Held-out: full_eval_010..012, five characters A10, same pair, $5 / 20000 calls. Promote only with no new errors, meaningful mechanical checks and no paired strength regression; zero victories means exploratory progress only.

Native adapter correction before deployment: native nonattack intents use null damage/hits; sum explicit total_damage or zero instead of headless intent fields. Headless development v1 remains the original immutable implementation, unaffected by this native-only correction.

Development v1: all10 normal defeats, no errors; raw Jev mean8.8 floors versus guarded8.6 (one lower, four ties), zero wins. Cost $0.150027150/1088calls. No promotion based on this result. Keep the predeclared held-out test to distinguish the concrete early-end correction from net strength; all failed/outperformed cases remain included.
