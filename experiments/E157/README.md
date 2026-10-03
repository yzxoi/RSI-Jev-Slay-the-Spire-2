# E157 — Current-runtime Map saves and short-prefix restoration

Issue [#302](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/302). Compatibility/performance only; no teacher strength, training or live-game claim. Depends on E149 root infrastructure and E154 runtime.

## Protocol frozen before any E157 game execution

Hypothesis: the existing native Map-save mechanism, rebuilt for the exact current runtime, can restore both combat and reward roots without replaying every earlier floor. Use all30 fixed E149 bank-v1 roots from15 Ironclad TRAIN seeds(A0/A5/A10×5). No substitute roots or edited saves; unavailable Map boundaries fail completeness. Pick the latest genuine Map boundary preceding each root. Preserve original seed/ascension/RNG/HP/deck/rewards.

For each root use two distinct first actions: E149 candidate0 and candidate1. Reference A uses full-prefix restore then the frozen BC1702 actor through actual full-run victory/death; candidate0 follows greedy, candidate1 samples with seed15700000+root_index. These are fidelity trajectories, not independent victories or a new strategy comparison. Capture B repeats full-prefix restoration, writes a native save at the selected Map, then checks every response through the root and replays the complete A suffix. Both B paths must exactly match A, including rewards and later draws where reached. Keep B0's immutable native save for both policies; B1 is additional save-call side-effect evidence.

Commit all60 A/B reference pairs and30 snapshot identities before C. For each A suffix, two independent fresh-process C loads of B0's save must reproduce every response from loaded Map through root, complete suffix and final state. A replayed local path is not an independent game seed. No opaque observation-hash transpositions or arbitrary combat-memory snapshots.

After all C checks, make2 paired full-prefix A / save-plus-local-prefix C timing measurements per root, alternating order by(root_index+repeat)%2; stop at the exact root before taking any action. Do not exclude slow samples. Gate: all30eligible, all60 B and120 C paths exact, native identities/bytes unchanged, all120 timing paths exact, zero exceptions/caps/timeouts, median paired restoration speedup>=2 and pooled C p95<=A p95. Report timing clusters/correlations; this is scoped reuse, not universal engine certification. No warm persistent reset (E129) or runtime/game DLL changes.

Budget:4workers,90s/full suffix,30s/restore timing,900s cumulative gameplay wall across capture+verify,1800s cumulative parent+child CPU. Stop launching paths on exhaustion; retain missing/failed cases. Raw saves and full plans stay ignored. Commit implementations before execution and reference manifest before verification. Only a passing immutable index may be used in a separately recorded E149 rerun; E149 seeds/continuation streams/statistical thresholds stay fixed, previous attempts remain separate. Final330 acceptance seeds unused.

Commands:
```sh
python3 scripts/validate_teacher_maps_e157.py capture --output artifacts/runs/e157-capture-v1.json
# Commit the capture manifest before independent verification.
python3 scripts/validate_teacher_maps_e157.py verify --capture experiments/E157/capture-v1.json --output artifacts/runs/e157-verification-v1.json
```

## Capture v1

Tested `bab9ad3c28c387322213d2f840fb80106400e4e1`:all30 roots have genuine preceding Map boundaries;60 full reference suffixes and60 independent save-call replays complete and match every state/final hash.120raw bundles audit. Capture140.740s/166.242CPU seconds. Native seed/ascension identities preserved; game/runtime binaries unchanged. Freeze all reference-plan and native-save hashes before C loads and paired timing. This passes save-call invariance only, not loaded recovery or speed.

## Verification v1 — fidelity failure, reuse forbidden

Tested0078011:112/120 C paths match;8 repeatable failures belong to the combat and preparation roots of `e149_train_Ironclad_A0_002`. At map coordinate(2,13), the original run enters a Monster room with Axe/Assassin/Brute Raiders; loaded runs enter the Dense Vegetation event. The preparation root itself matches before this later divergence. Thus visible root-hash equality alone is insufficient. No timing run is launched, no snapshot index is exported, and E149 cannot use these saves.240raw bundles audit;74.623s verification,215.364s cumulative gameplay. Keep all failures and locate the underlying adapter/native-save behavior separately; do not whitelist the28 passing roots into the complete30-root experiment.
