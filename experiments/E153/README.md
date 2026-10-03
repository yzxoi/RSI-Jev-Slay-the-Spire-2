# E153 — Real encounters, preparation credit and full-run monitoring

Issue [#290](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/290).

## Objective and hypothesis
Replace arbitrary six-battle curriculum endpoints with genuine ordinary/elite/Boss combat outcomes, attach macro preparation to the next real fight, and measure complete runs after every stage. Test whether this provides useful policy learning without pretending local wins are full-run competence.

## Fixed cohort and controls
Ironclad training: existing E133 TRAIN only (first Monster and first Elite/Boss per seed), E139 Ironclad TRAIN Boss roots, plus54new natural collector runs (A0/A5/A10×18) using the existing combat planner and cautious fixed macro routing. New local DEV bank:36collector runs (A0/A5/A10×12), kept out of training. Collector seeds e153_{train|dev}_Ironclad_A{a}_{i:03}. All collection runs continue to natural full-game victory/death, with no HP/reward/RNG edits; missing encounters and failures remain recorded. Single-battle and preceding-preparation roots derive only from genuine histories; no boss spawning.

Two learners2301/2302 start at the same frozen BC1702 policy; E152 critic is not promoted. Same e140 encoder/115,778-parameter actor-critic and PPO as E146 (lr1e-4,gamma=lambda1,clip.2,4epochs,batch128,entropy.01,value.5,gradnorm.5,targetKL.03). Reset critic head only. Three fixed stages, two24-episode updates each: Monster(12combat+12prep-Monster),Elite(6Monster+12Elite+6prep-Elite),Boss(6Monster+6Elite+6Boss+6prep-Boss). Fresh on-policy actions each episode; deterministic cycling over TRAIN roots, no outcome-based root selection. Total288training episodes across both learners. Training starts only if every encounter class has>=3independent TRAINseeds and each preparation class has>=1root; all gaps by difficulty/act are reported. Preparation allows all legal routes and stops at the actual next fight, so reference target class can change and must be reported.

## Boundaries and evaluation
Combat episodes terminate at the first genuine win/death; preparation episodes start at the preceding battle reward boundary (or Neow for first fight), execute all legal macro actions, and terminate after the next genuine fight. The final fight reward is not an action in that episode: reward choices instead belong to the subsequent preparation episode. Target -1 on death,1+.25remainingHP/maxHP on clear,matching existing local battle utility; also record potion/gold/deck inventory, not claim HP-only utility captures full-game value. No six-battle target. Enforce no success at an initial reward menu or in-combat reward interruption.

Fixed recurring-in-training DEV full-run panel:9new seeds(A0/A5/A10×3), baseline then each of3stage checkpoints; no checkpoint selection or schedule changes from DEV. Final TEST after final hashes committed:33different seeds(A0..A10×3), initial BC,each final learner,and existing cautious planner=132complete-run attempts. All phases actor-controlled for neural arms. Local DEV panel deterministically picks first root per seed/type,up to12per encounter type plus preparation counterparts; compare initial/final actors. Boss DEV scarcity is explicitly inconclusive,never filled from TRAIN.

## Gate / budget
Require execution integrity,>=3held-out Boss seeds for local generalization,each learner >=2additional Act2 arrivals versus initial over33TESTseeds,no >1Act2-arrival regression in any difficulty,and no lost full-game victory; local combat clear count must not regress for any class. Full-run win counts reported separately; any promotion still requires stronger follow-up,never claim final A0-A10 acceptance. If gate fails,stop this recipe expansion and keep default unchanged. Final330acceptance seeds remain unused.

Budget:collection900s/8workers,bank building180s,training+DEV monitoring1800s (max900s each learner),final/local evaluation900s; each restored episode60s/300decisions,full run180s/2400decisions. First-stage first episode per learner and first local/full evaluation per difficulty independently replay; raw trace and weight hashes retained. Full-prefix restoration is used for arbitrary reward roots and counted explicitly; prior native-map certificates do not certify these new starting states. No silent reset fallback or resampling. Every implementation/fix iteration committed before evaluation; result comment before merge/close.


## Implementation choices frozen before execution

Encounter roots are the first Monster/Elite/Boss per selected natural source seed; preparation roots start at the preceding actual clear boundary, or original Neow before the first fight. For scheduling and local panels, root lists interleave difficulty buckets in sorted seed/case order. Route choices remain legal/unforced, and actual encountered class is logged separately from the reference class. No policy outcomes select roots. The new bank is TRAIN-only for fitting; local DEV roots come exclusively from the36new collector DEVseeds.

The first6TRAINstrata (combat/preparation × Monster/Elite/Boss) are verified by greedy BC continuation plus an independent action-by-action replay before training. Full-prefix restoration verifies the actual root hash on every episode; no native save is assumed compatible with arbitrary reward starts. Earlier engine versions are accepted only through exact current-engine root/continuation verification. Restoration time remains measured, not treated as inference cost.

Three stages each contain two24-episode on-policy updates per learner. All legal reward/card/potion/map/rest/shop actions encountered in preparation participate in policy gradients. Source actor weights and architecture remain unchanged at initialization; only the value head is reset. ExistingE152 critics/encoder are not deployed. Stage DEV panels are fixed, descriptive and never select checkpoints or alter schedule. Final frozen actor checkpoint is evaluated even if stage monitor outcomes were poor. Runtime failures stop the affected learner rather than removing paths. This isolates a curriculum/coverage package, not one causal ingredient or comparison against a freshly retrained six-battle arm.

## Reproduction

```bash
python3 -m unittest discover -s tests -p test_curriculum.py
python3 scripts/train_curriculum_e153.py plan --output artifacts/runs/e153-plan-v1.json
# Freeze each stage's complete public input manifest before the next command.
python3 scripts/train_curriculum_e153.py collect --plan experiments/E153/plan-v1.json --output artifacts/runs/e153-collection-v1.json
python3 scripts/train_curriculum_e153.py bank --plan experiments/E153/plan-v1.json --collection experiments/E153/collection-v1.json --output artifacts/runs/e153-bank-v1.json
python3 scripts/train_curriculum_e153.py train --plan experiments/E153/plan-v1.json --bank experiments/E153/bank-v1.json --output artifacts/runs/e153-training-v1.json
# Freeze final weights before evaluation on the33untouched test seeds.
python3 scripts/train_curriculum_e153.py evaluate --plan experiments/E153/plan-v1.json --bank experiments/E153/bank-v1.json --training experiments/E153/training-v1.json --output artifacts/runs/e153-evaluation-v1.json
```

## Collection v1: integrity stop before training

Tested SHA `93a9c28`; all90fixed seeds completed in91.632s.88natural defeats,2execution errors;14Act2 arrivals,1Act3 arrival,45Boss entries.96raw bundles (including6independent replays) hash-audited. No training or policy improvement claim. `max_floor` is the maximum **within-act** floor, not total floors travelled.

Frozen errors: `train-A0-011` stalls on original ReattachPower animation method JIT because Godot.Node.GetIndex(bool) is missing; `dev-A0-002` errors on Trial.Accept's unguarded NEventRoom UI access. The latter also has an earlier unobserved Crusher.AfterAddedToRoom JIT failure for CanvasItem.SetVisible(bool), potentially skipping its original power application. Thus even successful state responses are not sufficient evidence of engine integrity. Keep both original paths and hashes; do not remove or substitute seeds. Training is stopped. A separate compatibility experiment will add exact guarded ABI signatures, compare unchanged histories, verify original Crusher powers, and rerun the identical90seeds before any curriculum fitting. Trial UI access remains separately tracked if encountered with the corrected combat semantics.

## Collection v2 amendment before fitting

Use E154 guarded ABI fix (dependentPR#293, merge1dda233) and the separately frozen `collection-v2.json`. Fixed seeds, all learning/evaluation settings and gates remain plan-v1. Collection at50db5d7:90natural defeats,14Act2 arrivals,0Act3 arrivals,47Boss entries in83.447s. E154 validates88unchanged histories and both corrected paths; old Act3 arrival was an invalid skipped Kaiser Crab fight. No seeds excluded or replaced. Trial event remains a known unsupported path (#294), with fail-closed runtime exception detection. Successful current cohort does not certify every game mechanic.

Continue bank/training under corrected assembly/stub hashes, full-prefix root validation on every episode. `collection-v1` stays failed and must not supply new roots. No policy promotion from this compatibility fix.

## Frozen natural bank

Bank/preflight tested at eb9855d,19.609s. TRAIN:246Monster roots (82per A0/A5/A10),178Elite (56/66/56),28Boss (15/8/5); each has a separate preceding-preparation root,904TRAIN roots total. DEV:36Monster,23Elite,19Boss (156roots total). All Boss roots are Act1; only2TRAINElite roots are Act2. This is a staged first-act pilot, not coverage of all acts. Six fixed-stratum continuations and independent replays passed,12trace bundles audited. Every later episode must verify its exact natural root again. Freeze bank before two learners and recurring full-run monitors.

## Training v1 integration stop

At9b2dd0a initial9full runs all defeated; learner2301 completed48ordinary/preparation paths,all cleared (update returns1.19865/1.18828). Before its first stage monitor, strict checkpoint reload failed: saved E153 manifest omitted the required encoder version. No further stage/TEST execution occurred; weights, optimizer/RNG and all paths remain intact in v1. This is serialization failure, not training success or game defeat.

Iteration v2 adds the existing e140 encoder identifier to the manifest and immediately round-trips each saved checkpoint. Restart the identical bounded pilot from unchanged source/learner seeds/configs, preserving v1; no selection or resampling from outcomes. The first48new training paths/weights must match v1 exactly (apart from metadata), so the small restart does not hide trajectory changes. Report duplicate compute separately and do not count it as independent training data.
