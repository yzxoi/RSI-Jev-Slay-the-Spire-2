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
