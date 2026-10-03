# E152 — Shared attributes for critic generalization

Issue [#288](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/288).

## Hypothesis
E148/E151 exposed severe critic generalization failure not explained by novel item identities. A compact shared-attribute, role-pooled observation (same attributes share channels across card IDs; token-level effect features) reduces memorization and improves frozen-policy return prediction versus the existing identity-path hash representation.

## Fixed experiment
E152 only changes the observation representation within matched new models. Same 545->128->128->1 Tanh MLP (86,529 parameters), two initialization/shuffle seeds 2201/2202, same initial weights within each pair, 24 epochs, Adam3e-4, batch512, norm1, trajectory-balanced MSE, CPU1. Both arms start from identical random trunks and zero value heads because BC input weights are not comparable under a new representation. Both receive explicit task progress/ascension. Compare hash versus shared. Retain frozen E148 task critics as additional practical controls; do not conflate the random-initialized control with E148's BC initialization.

Only original E148 TRAIN216 game seeds /432 paths train either arm. No new target/actor optimization, early stopping, hyperparameter selection, terminal overrides or checkpoint selection. Fresh test seeds e152_test_Ironclad_A{0,5,10}_{000..023}, each two actor sampling streams (144 paths /72 distinct seeds). Sampling seed 152000000+asc*10000+index*10+rep. Freeze weights and baseline coefficients before collecting/scoring fresh test. Same frozen BC1702 behavior actor, full phases, six actual clears after rewards or natural death, original terminal labels. E148 DEV is already inspected and is not fresh test. Final330 acceptance seeds untouched. Three independent replays (each ascension index0 rep0).

## Baselines and gate
TRAIN-fitted constant and fixed alpha.01 progress ridge; frozen E148 task critics; paired newly trained hash controls. Same complete test trajectories for every predictor. Primary MSE is equal-path-weighted, bootstrap clustered by72 game seeds (2,000 resamples seed152). Both shared learners must reduce MSE >=10% vs paired hash, >=5% vs better simple baseline, not exceed paired E148 task MSE, have paired improvement CI upper<0 against hash and the better simple baseline, and no difficulty MSE >110% paired hash. Raw post-six-clear MAE<=.25 on >=10 distinct test seeds. Report phases/endpoints, fit gap and counts. All selected failures/stalls retained; incomplete execution blocks promotion, never replaced. Gate failure stops expansion of this recipe; passing only permits a separate actor/search experiment, never claims improved gameplay.

## Budget / recording
Preprocess180s, fit180s, fresh collection450s (8 engine workers, each180s/2400 actions), score120s. Preserve input/model/tensor/raw hashes and all coherent implementation/repair/result commits. One PR, result comment before merge/close. No visible game actions or overlay. New representation is still lossy and token hashing is not language understanding; this tests a representation package, not each feature's causal effect.


## Representation and causal scope

Both new arms have 540 observation +5 task inputs, exactly86,529 parameters. Shared input keeps20 existing scalars,9 explicit phase indicators,7 resource/context scalars, and seven72-channel role pools:hand,deck,enemies,player powers,owned potions,owned relics,offers. Entity channels include presence,23 shared numeric/categorical properties,16 stat-name hash slots and32 effect/name token hash slots. Fixed role scaling and clipping; no fitted vocabulary/normalization, no outcome input, IDs not used in attribute keys. Pooling preserves multiplicity but loses within-role entity identity and some relations/order. Bundle grouping is lost. Token hashing is not language understanding and does not implement mechanics. The representation package includes previously ignored text attributes and explicit phases; success cannot be attributed to any one component without further ablation.

Fresh TEST is genuinely new and generated only after weights freeze. E148 DEV is not used for fitting or checkpoint selection. Main contrasts share initialization/loss/optimizer/budget; comparison to older E148 critics additionally differs in initialization. Raw values remain unbounded and no task-boundary override is introduced, to keep the comparison about representation.

## Reproduction sequence

```bash
python3 -m unittest discover -s tests -p test_shared_value.py
python3 scripts/probe_shared_value_e152.py plan --output artifacts/runs/e152-plan-v1.json
# Commit the plan before preparation.
python3 scripts/probe_shared_value_e152.py prepare --plan experiments/E152/plan-v1.json --output artifacts/runs/e152-prepared-v1.json
# Commit the prepared manifest before fitting.
python3 scripts/probe_shared_value_e152.py fit --plan experiments/E152/plan-v1.json --prepared experiments/E152/prepared-v1.json --output artifacts/runs/e152-training-v1.json
# Commit final weight hashes before new game collection.
python3 scripts/probe_shared_value_e152.py collect --plan experiments/E152/plan-v1.json --training experiments/E152/training-v1.json --output artifacts/runs/e152-bank-v1.json
# Commit complete fresh bank before scoring.
python3 scripts/probe_shared_value_e152.py score --plan experiments/E152/plan-v1.json --training experiments/E152/training-v1.json --bank experiments/E152/bank-v1.json --output artifacts/runs/e152-evaluation-v1.json
python3 scripts/probe_shared_value_e152.py plot --training experiments/E152/training-v1.json --evaluation experiments/E152/evaluation-v1.json --output experiments/E152/figures
```

All raw arrays, weights and gameplay traces stay under ignored artifacts/runs; public manifests preserve their hashes. Default actor/CLI/native policies are unchanged.
