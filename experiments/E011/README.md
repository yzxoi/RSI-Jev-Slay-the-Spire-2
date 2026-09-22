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
