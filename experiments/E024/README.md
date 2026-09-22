Hypothesis: current one-turn beam score values 1 HP lost at only 1.5 versus 0.85 per damage, which may spend too much life on nonlethal attacks. Compare planned baseline to cautious with loss penalty 3.0, identical beam width/depth and all other behavior. This may regress racing/scaling fights; measure full-run outcomes rather than predicted score.

Fresh fixed heldout full_eval_022..024, all five characters A10, 30 full runs, matched identical model requests, budget $3/12000 calls, 2 workers. No sample pruning. Promote only with zero new errors and better paired reach/wins; zero wins remains a limited first-act result. Separate implementation/results commits and raw traces. Native run continues independently, without applying this unvalidated score change.

Issue #43. Only loss_weight changes 1.5→3.0; no mechanics, engine, rewards or HP modifications.
