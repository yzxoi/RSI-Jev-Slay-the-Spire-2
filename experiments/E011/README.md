# E011 — Full-run evaluation and scene coverage

Issue #17. Milestone 1 accepted; repository is now public at the user's request. Objective: complete high-ascension runs, distinguish normal defeat from execution failure, and expose every supported macro decision to traceable policies.

Iteration 1: reuse E003's limited numerical comparator (not its rejected Jev feature prompt), add full-run scene candidates and a Jev macro option. Fixed baseline uses first playable in battle, first card reward, safe local routes, heal below 65%, otherwise upgrade, and no shopping. Greedy changes only combat to the prior numerical rule; hybrid additionally lets Jev choose noncombat actions using the same supplied state and strategy instruction. No causal strength claim is made from a comparison changing both components.

Fixed development input: all five characters, A10, `full_dev_001`, first/greedy then hybrid. Validation: `full_eval_001..003`, five characters, A10. 4,000 steps per run; initial combined Jev budget $3 / 12,000 requests. Infrastructure promotion requires normal terminal outcomes with no remaining adapter errors and focused tests of reward/selection/shop legality. A victory is the engine's normal terminal result, not a modified HP/victory value.

Known headless limitations: gold/potion/relic rewards and treasure relic choice are partly auto-resolved by upstream; potion capacity is not exported so this iteration excludes shop potion purchases; pending card selection exports no semantic prompt, so previous action context is supplied. Multi-card combinations are capped at 128 per size. No arbitrary cloned-state simulator is claimed. Live MCP has its own richer scene adapter in E013.

```sh
python3 -m unittest discover -s tests -v
python3 -m rsi.full --policies first,greedy --seeds full_dev_001 --output experiments/E011/development-v1.json
python3 -m rsi.full --policies hybrid --seeds full_dev_001 --output experiments/E011/hybrid-v1.json
```

## Iteration 1 outcomes

Implementation a6c2cae: development 15/15 normal defeats, no wins; validation 26 normal defeats and 4 infrastructure errors out of 30 selected runs. All reports and traces preserved. Validation exposed two distinct problems: combinatorial card-selection criteria duplicated full card metadata (185,144 JSON characters, provider 400), which tripped the shared unknown-usage budget; and repeated Jungle Maze Adventure choices with no state progress. Two other runs stopped due to that shared budget guard. These are errors, not losses. No promotion yet. Next fix compacts selection references and supplies a bounded selection count; event progress needs separate diagnosis without silently changing game outcomes.

## Iteration 2 changes

Selection candidates now reference card indices/names; the complete card definitions already occur once in state. This removes the 185 KB duplicated request. Inspection found the headless event adapter invokes `EventOption.Chosen()` directly, while the native game bridge uses `EventSynchronizer.ChooseLocalOption(index)`. Patch only the upstream adapter to use the native synchronizer (tracked reproducible patch); no event outcome is synthesized. Record built assembly and patch SHA-256 in manifests. Also inspect engine diagnostics so the upstream deadlock fallback's forced game_over cannot masquerade as normal defeat. Previous 45 stderr logs contain no such fallback. Rerun the previously fixed validation set as integration regression, not a new held-out strength test.

Iteration 2 result (d13d50d): selection request no longer fails; 27 normal defeats and 3 unchanged-state event errors, 0 wins. The synchronizer patch did NOT solve Jungle Maze Adventure. Keep this unsuccessful fix in history and investigate the specific event continuation rather than filtering the seed out. Built assembly hash pins the actual tested binary.

Iteration 3 diagnosis: local inspection of the owned game binary identifies Jungle Maze's safe option calling the debug-audio singleton before awarding gold; headless has no NGame/DebugAudio receiver. The new adapter patch provides an inert receiver and suppresses cosmetic Play only; the original event still awards its own gold, applies its own HP changes and finishes itself. Do not copy proprietary decompiled source into Git. Verify the exact stalled action prefix and expected state transition before re-evaluating complete runs.

Iteration 4 resilience: E012's larger concurrent batches exposed transient provider EOF/timeouts. Add opt-in bounded inference-only retries (at most two), recording each request/failure. For these full-run batches, reserve and charge the published maximum-input cost for every uncertain response; report estimated cost separately from provider-reported cost and preserve the unknown flag. Game actions are never retried by this change. The default strict budget behavior remains for existing callers. This avoids one uncertain inference disabling every later batch row while respecting a conservative spending cap.

Iteration 3/4 evaluation failed at Neow (15/15 infrastructure errors): the inert audio receiver exposed a missing Godot stub setter while Harmony tried to compile Play, so the cosmetic method was not intercepted. A prefix replay also stopped before reaching the target event (`No pending bundle selection`); no replay-consistency claim. Preserve this failed build's manifests. Next fix removes only the cosmetic audio Play body in the copied headless DLL before JIT, using the existing Mono.Cecil setup pipeline; the original Steam DLL stays untouched.

## Final infrastructure validation

Tested 11364d6. All 15 preselected five-character A10 runs in validation-v4 ended in normal defeats, zero adapter errors, zero wins. Scene counts: {'event_choice': 44, 'card_select': 43, 'map_select': 123, 'combat_play': 1856, 'card_reward': 80, 'rest_site': 12, 'game_over': 15, 'shop': 5, 'bundle_select': 5}. Provider accounting: {'requests': 226, 'cost_usd': 0.033319692, 'unknown': False, 'estimated_usd': 0.0, 'uncertain_calls': 0}. The exact formerly stalled Jungle Maze action prefix now resolves to map: HP 70→70, gold 149→187, matching its +38 gold variable; the game event itself applies the result. Fixture trace and manifests retained.

Decision: merge infrastructure, not a strength claim. Eleven focused unit tests pass. The selector, full-run traces, error classification, reproducible cosmetic headless patch and bounded inference accounting now support strategy experiments. Upstream headless still auto-collects some rewards and is not proven identical to native gameplay for all mechanics.

Additional scene found in E012's broader seed set: Dense Vegetation calls cosmetic debug-audio Stop after healing. Extend the same local IL audio shim to Stop; original healing and combat transition remain untouched. The prior 15-row suite passed but did not exercise this scene, so broaden its compatibility verification before merging.
