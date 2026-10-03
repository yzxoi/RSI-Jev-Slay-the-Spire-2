# E147 — Credit assignment and AlphaZero design audit

Hypothesis: E146 execution was valid but its observed lack of greedy held-out improvement may reflect weak/biased task targets, low effective actor signal, value miscalibration or action-level regressions. Diagnose these separately before claiming terminal-return RL is intrinsically wrong or adopting AlphaZero search training.

Frozen evidence: every E146 training record (1152 trajectories, both learners, all12updates) and every DEV record (180 attempts, shared30game seeds), their raw decision/wire hashes and before/after checkpoint hashes; E145/E128/E142/E143 only as explicitly labeled historical references. No new gameplay, gradients, seed replacement, checkpoint selection or full-run victory claims. DEV is descriptive diagnosis, not future untouched test data.

Predefined measurements: outcome/length/phase/difficulty coverage; multi-option vs forced actions and entropy; raw and batch-normalized Monte Carlo advantage signs and mass by phase/difficulty; old-value MSE and explained variance versus return-mean baseline; first-state and terminal-near predictions; target-six-cleared pending reward decisions; recorded lethal last actions and legal alternatives (descriptive, no counterfactual claim); all paired greedy success gains/regressions, earliest shared-state action divergence; initial/final actors re-scored on fixed TRAIN first-update i00 at each difficulty (actual probability changes, no new outcome inference). Also verify encoder source fields/remaining-goal representation. CPU only;900s read/re-score budget; retain coverage failures without silently sampling. No model updates.

Compare findings to primary AlphaZero, MuZero/Reanalyse, GAE and limited-budget search literature. Distinguish terminal value supervision, search backups, policy visit-distribution targets and learned dynamics. Existing simulator and our previous failed search/distillation constrain proposals; no general effectiveness claim from changing algorithm names.

Decision: publish a reproducible descriptive audit and evidence-ranked redesign recommendation. Never treat correlations or same-trajectory future divergences as causal blame. Register any new engine intervention or training idea separately before testing. Infrastructure/audit validity and policy strength remain separate; default gameplay unchanged. Original final330seeds remain unused.

Issue278. Read-only implementation includes exact decision/wire/action-index alignment and all source hashes. Three synthetic tests cover calibration baselines, forced decisions, sign accounting, degenerate target variance and list-valued menu labels. Full command after implementation commit: `python3 scripts/diagnose_credit_e147.py --output artifacts/runs/e147-diagnosis-v1.json`. All fixed cases retained.

Diagnostic v1 (6f30bfb) stopped before completing its first batch: candidate `details` can be a list; the label formatter assumed dict. Original log hash in attempt-v1.json; no game actions or weights affected. v2 handles list labels and reproduces original GAE/torch normalization exactly, same complete cohort. Added regression test;3 tests pass. v2 command: `python3 scripts/diagnose_credit_e147.py --output artifacts/runs/e147-diagnosis-v2.json`.


## Results and decision

- Complete raw audit v2 at `a9de5ca3570101da4312ee4b7a476a8cc01c482f`: 27.850 seconds CPU, all 1,152 TRAIN episodes /103,127 decisions and180 DEV attempts;1,350 source bundles and51 referenced model/optimizer checkpoints pass. No new game actions or gradients. M3 Max64GB,Python3.13.5,PyTorch2.11.0,NumPy2.3.2; dependency/game/DLL hashes in the result manifest (historical v0.111.0).
- Keep full local raw diagnosis at `artifacts/runs/e147-diagnosis-v2.json`; publish compact derived statistics plus all60 paired earliest-divergence records and five trace excerpts in [diagnosis-v2.json](diagnosis-v2.json). Each excerpt links source hashes. Publication/plot code `8cdfe42` records the source file hash; intentionally omitted repeated fatal/rescore rows remain locally recoverable.
- Of103,127 decisions,23,604 have one legal action.995 training deaths include904 forced last actions.85/90 DEV Act1 deaths have a forced last action. These counts do not establish an earlier causal mistake.
-157 successful training trajectories contain235 post-sixth-clear reward decisions: all positive normalized advantages;V mean−0.318 versus realized reward+1.098. Updates9–12 still predict−0.291 /+0.031 against+1.092 /+1.116. Controller/encoder source lacks explicit goal, remaining battles and ascension. Causality of that omission is untested.
- Last-batch pre-update EV is0.238 /−0.031; pooled−0.059 combines changing policies and cold-start critic. Report actual per-update improvement and instability, not “critic learned nothing.” Greedy DEV and stochastic TRAIN are different continuation policies.
- Read actual paths, not just final labels: onA5_04 the first action divergence swaps Bash/Defend order with the same observed turn-end HP/block/enemyHP; onA10_09 the later-losing1902 actor kills a13HP enemy a turn earlier and exits combat at the same74HP as the eventually successful baseline. First divergence and final reward are not a causal root-action label.
- AlphaZero retains terminal outcome value supervision, but actor targets are search visit distributions. MuZero/Reanalyse and limited-budget mctx are primary-source comparisons, not demonstrated STS2 improvements. Prior E128 search and E143 hard-BC failures constrain the recommendation.
- Decision: accept diagnostic infrastructure and evidence; no policy promotion, no new training. Proposals E148/#279, E149/#280, E150/#281 are registered but unexecuted; exact manifests/thresholds must be frozen before their own evaluation. Final330 acceptance seeds remain unused.

Full Chinese [diagnosis, source links and ordered proposals](../../docs/research/learning-search/2026-10-03-credit-and-search.md). [Figure](figures/credit-diagnosis.png) visually inspected;3 synthetic tests pass, compilation and diff check pass. Failed v1 remains in history; no retries touched gameplay or models.

```bash
python3 -m unittest discover -s tests -p test_credit_audit.py
# Choose a new ignored output path; audit deliberately refuses to overwrite evidence.
python3 scripts/diagnose_credit_e147.py --output artifacts/runs/e147-diagnosis-reproduction.json
# Choose a new directory for publication; preserves checked-in diagnosis-v2.json.
python3 scripts/publish_credit_e147.py --source artifacts/runs/e147-diagnosis-reproduction.json --output artifacts/runs/e147-publication-reproduction
```
