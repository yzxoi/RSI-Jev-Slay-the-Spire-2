# E013 — Real full-run MCP campaign

Issue #19. User authorized continued gameplay through all rewards, selections and rooms until a genuine complete victory. Start from existing Ironclad A0 run `9JKXVG5BK1D8`, floor 3, 74 HP. This continuation is not an A10 validation run and its opening was played before this experiment.

Iteration 1 adds an all-scene native adapter and a budgeted single-writer complete-run controller. Jev chooses combat and macro actions, using E011 macro guidance; forced scene progression does not call the model. It records each response/state and stops on death, victory, expert-needed lethal end turn, unclear delivery, unsupported scenes, or budget. No resets, HP edits, rewards injection or debug victory flags. First segment cap 150 actions / 3,600 seconds / $3; inspect trace before further segments. Subsequent strategy versions are recorded per segment, never advertised as one fixed-policy benchmark.

PR is stacked on E011 for the shared macro instruction. Promotion requires a real complete victory plus trace/native-state corroboration and scene adapter checks; failures remain part of the report. Different strategies or character restarts must be reported explicitly.

## Segment 1 result

Tested cbe0a91. 48 accepted actions, 45 Jev requests, $0.009080274, 160.136 seconds. Rewards and card choices completed at floors 3 and 4, Armaments combat upgrade selections resolved, and battle continued at floor 5. Controller stopped on another explicit legality rejection (`Action is not available in the current state.`) after a readiness race. No uncertain command was replayed. Remaining HP 42. The complete failed segment is preserved. Trace also shows early end-turn choices with playable cards; a numerical turn-planning experiment will evaluate that separate tactical weakness before resuming.

Iteration 2 transport fix: native `ExecutePlayCardAsync` also checks readiness before touching any card and returns a different exact error envelope. Extend recoverable rejection classification only to that audited play_card/COMBAT error, retaining stop-on-uncertain-delivery behavior. Add positive and negative regression cases.

Iteration 3 tactical application: use the experimental E012 planner (d7fac79) for native combat, replan after every action, keep Jev for macro choices and per-turn potion use. Fixed-macro A10 development improved mean first-act floor 12.2→14.2, with 0 wins; this is provisional live application, not a promoted high-ascension policy. Native adapter estimates damage modifiers from supplied dynamic values/powers and records its limitations. Baseline live Jev remains selectable. Incorporate E011 bounded inference retries and report uncertain-cost reserves separately. Continue same battle at 42 HP; no reset.

Segment 2 (9e7afe5): 17 accepted actions, 5 Jev calls, $0.000924210. Finished the existing battle, claimed rewards and entered floor 6 with 42 HP. Non-attack native intents carry null damage/hits; the headless numerical helper expected absent/default or numeric fields and raised TypeError. Controller stopped before issuing an action at the new combat. Fix the adapter to normalize null non-attack previews to zero, with a regression case.
