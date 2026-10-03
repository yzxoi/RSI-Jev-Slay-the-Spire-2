# E151 — Item novelty and the E148 critic generalization gap

Issue [#286](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/286). Read-only post-hoc diagnosis requested after E148: can unseen card/potion/relic identities explain the held-out error gap? This is not a training, gameplay or causal intervention experiment.

## Frozen protocol

- Inputs: all original E148 432 TRAIN paths / 216 seeds and 144 DEV paths / 72 seeds, A0/A5/A10; no substitutions. Existing frozen predictions for four critics, constant and progress ridge. Verify bank, tensors, prediction and raw trace hashes; align every decision to the original wire/action. No new games, inference, gradients or use of final acceptance seeds.
- Build the identity dictionary from TRAIN only. Base card/potion IDs use unambiguous TRAIN name aliases where menus omit IDs; relics use exported names when IDs are absent. Upgrades do not count as new base identities. Fail on missing/conflicting identities. Report separately owned objects and all explicit visible objects, including rewards/shop/bundles. Textual event references, powers/enemies and hidden state are outside this identity audit.
- Count novel identities, affected decisions/paths/seeds and frozen prediction error in known versus novel item states, entirely known paths, and post-sixth-clear states. Keep original E148 equal-path weights for additive error attribution; explicitly label normalized within-group MSE. Count new owned inventory compositions including deck multiplicity/upgrades, potions/relics, without equating familiarity with sufficient learning.
- Decision rule: if most DEV squared error remains on fully known visible identities and task critic MSE there exceeds the better simple baseline, reject new identities as a sufficient explanation, while retaining possible contributions. Otherwise attribution is inconclusive. No causal claim or gameplay policy promotion in either case.
- Budget: 180 seconds read-only computation. Preserve all source evidence. Commit implementation before the audit and results afterward. E149/E150 remain unexecuted.

```bash
python3 scripts/audit_item_novelty_e151.py --output artifacts/runs/e151-novelty-v1.json
```

The scope is E148 critic TRAIN exposure, not all earlier actor pretraining. An identity may have appeared only as a menu option or on a few correlated decisions. Novel numeric states, combinations, enemies and RNG can remain even when every item identity is known.
