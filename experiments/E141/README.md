# E141 — Read-only internal observations before more learning

Issue265. Hypothesis: draw/discard/exhaust identities, complete map topology, ordered orbs and Osty are missing or collapsed by E140. Provide opt-in observations and encoding; this is representation/compatibility evidence, not a strength experiment or a claim of complete Markov state.

Baseline: unchanged engine ordinary responses and all15 E139 train-index00 full histories (five heroes × A0/A5/A10). CLI already has get_map; the new explicit get_learning_observation command reuses GetFullMap internally. No extra data added to ordinary replies, no RNG calls, action pumps, game value setters or preview mutations. Cards expose native pile order, ID, upgrade level, current cost, base stats and keywords. Orb queue capacity/ordered entities and Osty are included. Draw order can change under effects/shuffling and is not a promise of future draws.

Synthetic encoder checks vary pile order, orb order, Osty HP and a future route while holding immediate state/menu fixed. Encoder preserves E140 features plus12 numeric/512 ordered-hash state features and128 selected-map-node features. Position-specific dictionary paths retain order. Hash collisions and missing trigger/internal-counter details remain limitations. Old weights zero-extended; no trained checkpoint or default policy changes.

Fixed evaluation:45 complete replays max, each180s,900s global wall cap,8workers. For each of15 sources: ordinary replay once; enriched replay twice with repeated observation at every nonterminal state and comparison to existing get_map. Every ordinary response must equal historical state hash, including terminal defeat. The enriched histories must also match each other; all observation arrays/numerics finite; all encoded menus remain valid. Any mismatch/censor fails gate. Preserve prebuild runtime hashes in ignored artifacts/runs/e141-runtime-before/manifest.json; game binaries unchanged. No test/acceptance seeds consumed.

Commands after committing implementation: `.tools/dotnet/dotnet build vendor/sts2-cli/src/Sts2Headless/Sts2Headless.csproj --no-restore`; `python3 -m unittest discover -s tests -p test_rich_observation.py`; `python3 scripts/validate_observations_e141.py --output artifacts/runs/e141-observations-v1.json`.

## Result and merge decision

Tested SHA `e77255d`. Build passed (one existing nullable warning),3 synthetic encoder tests passed. All15 fixed histories ×3 modes passed:45full replays,7386 legacy states exactly equal,4894 extra observations with immediate repeats and cross-process history hashes equal. All45raw trace bundles audited. Wall50.199s. Game DLL/stub hashes unchanged; only adapter assembly changed. Default response schema remains unchanged; no training/checkpoints altered.

Merge the explicit observer and optional encoder. This removes verified input aliases but proves no gameplay improvement and not complete Markov observability. Pile modifiers/trigger counters not exported here remain possible omissions. `observations-v1.json` retains per-case/mode evidence and prebuild runtime hashes. Raw traces, local decompiled inspection and runtime backups remain ignored.
