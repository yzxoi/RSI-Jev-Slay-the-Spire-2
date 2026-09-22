# E012 — Current-hand turn planning

Issue #18. E011 single-action greedy undervalues setup, and E013's live Jev repeatedly ends turns with energy and useful cards remaining. Hypothesis: searching card order and energy allocation over the current hand improves outcomes without changing macro choices.

Iteration 1: width-40 depth-8 beam search with state merging. Evaluate damage/block/kill combinations, Bash-before-attacks, block-before-Body Slam, strength, draw/energy and powers. Execute only the first currently legal action, then replan on the real engine result. This is explicitly an approximate scoring model, not exact cloned simulation: random draws, character-specific triggers, orbs, minions, resurrection and many card mechanics are not simulated. Trace records searched plan and scope.

Development: `full_dev_001`, five characters A10, compare greedy/planfixed (identical fixed macro decisions), then hybrid/planned (identical Jev macro instruction). Held-out: `full_eval_004..006`, five characters A10, hybrid versus planned. 4,000 steps/run; $3 / 12,000 Jev calls; width/depth fixed before evaluation. Promote only with no new execution errors, non-decreased wins and improved mean progress; if both have zero wins call it exploratory improvement and expand rather than claim strong play. Known E011 event stall stays an error, not a filtered sample or a defeat.
