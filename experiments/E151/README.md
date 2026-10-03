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

## Result: unseen base item identities do not explain most of the gap

Audit code `88e807d8efa38e794ab184666abdde00be8a2fcf`; Python3.13.5/NumPy2.3.2, existing historical v0.111.0 data only. Exact source runtime, game/DLL hashes, bank/tensor/prediction hashes are retained in [novelty-v1.json](novelty-v1.json). Runtime10.234s,576paths/51,343decisions/1,152raw files verified,12,700DEV prediction rows aligned. Three synthetic identity contracts pass. No failed audit, new games, inferences or gradients.

| Explicit visible item kind | TRAIN unique | DEV unique | DEV identities absent from TRAIN |
| --- | ---: | ---: | ---: |
| Cards |231|185|21|
| Potions |51|50|0|
| Relics |150|119|2|

Only757/12,700DEV decisions(5.96%),14paths/10seeds, contain a new visible base identity;owned/hand objects alone:737decisions,9paths/8seeds. Entire paths with no new visible item identity:130/144paths over68seeds. The identity vocabulary includes offers, so seen is a weak standard, not evidence of sufficient training. No audit of the actor's earlier pretraining vocabulary was performed.

| DEV group | Task2101 MSE | Task2102 MSE | Progress ridge MSE |
| --- | ---: | ---: | ---: |
| All |0.53854|0.54650|0.41039|
| No new visible item in current state |0.53656|0.54487|0.41215|
| Entire path has no new visible item |0.52976|0.53672|0.39752|
| New visible item in current state |0.57524|0.57683|0.37760|

Group MSE is conditional using the original full-DEV equal-path weights.94.53%/94.60%of task squared error lies in currently known-item states;88.81%/88.66%lies on entirely known-item paths. Pure arithmetic: making all novel-item-state prediction errors zero would still leave full-DEV MSE0.50909/0.51698. This is error accounting, not a causal estimate of training a new encoder or changing gameplay.

Post-sixth-clear:27/28DEV decisions have no new visible item. Their original-weight conditional mean target+1.0924 is predicted−0.4612/−0.4986. These values use E151's original full-path weights and are not the same weighting as E148's within-subset equal-path endpoint means. New items cannot be a sufficient account of the endpoint failure.

New compositions remain common:10,715/12,700states(84.37%)have an owned inventory multiset absent from TRAIN;9,966states(78.47%)combine known visible identities with a new inventory. Inventory equality preserves exported deck upgrade flags/multiplicity and owned potion/relic identities, but ignores enemy,HP,hand order,RNG,etc. New composition states differ in phase/progress/return distribution; this association does not establish the cause of prediction error. Even seen-inventory task MSE0.40297/0.41189 is worse than ridge0.36816.

Decision: merge the isolated audit and evidence; retain E148's stop decision. Do not prioritize collecting a few missing potion types—none are missing in this DEV cohort. Representation, compositional coverage and stochastic terminal labels remain candidate explanations requiring controlled studies. The code confirms categorical hashed strings rather than language understanding; this is an architectural limitation, not a measured cause. E149/E150 remain proposals, no model/policy promotion or full-run strength claim.
