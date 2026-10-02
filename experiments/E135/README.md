# E135 — Rolling Boulder headless ABI compatibility

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/253

## Problem and hypothesis

E133 expanded-data certification reached a real Colorless Potion -> Rolling Boulder sequence at train-150-b8. Ending turn throws MissingMethodException for GodotObject.Connect(StringName, Callable, UInt32) and stalls. The original official RollingBoulderPower.AfterPlayerTurnStart already has a TestMode branch that calls its real DoDamage against hittable enemies, then increments Amount by Damage. The CLI sets TestMode.IsOn=true. The method also contains unexecuted visual-path calls whose signatures must exist for JIT compilation. GodotStubs exposes Connect only on Control with the wrong arity and CallDeferred only on Node with a different return type.

Hypothesis: add the exact required ABI signatures on GodotObject so the original game TestMode damage path can execute. The unavailable visual methods will throw if actually invoked, never silently swallow gameplay effects. Do not replace power logic, remove the card, mask legal actions or edit HP. Record GodotSharp stub SHA in new manifests and restore identity checks; existing three hashes do not cover this dependency. Original and patched proprietary game DLLs must remain byte-identical.

## Fixed implementation and validation scope

Create an additive managed source patch for GodotStubs/Core.cs, and update setup's allowed managed-file list. Add Error Connect(StringName, Callable, uint flags=0) and Variant CallDeferred(StringName, params Variant[]) guarded by explicit unsupported-visual exceptions. Add only further signatures if the same frozen method's JIT reveals another missing ABI, preserving each failed iteration/commit. Do not simulate the visual callback path or change TestMode/RunState behavior. Rebuild the local adapter with the pinned SDK and current historical game files; keep old assembly/stub hashes and a local binary backup.

1. Reproduce the exact train-150-b8 canonical prefix and four successful battle actions from its hashed E133 error trace. All pre-error observed states must remain exact. Execute the previously failing end_turn; require a genuine next player decision, original Rolling Boulder power progression/damage evidence, and no unsupported visual stub invocation or forced game_over. Continue using the same planner to the real battle terminal; independently full-prefix replay that complete new path three times. Every hash/outcome must match. This is one compatibility case, not a win-rate sample.
2. Recollect the entire unchanged E133 264-seed preparation cohort under the patched dependency, with original fixed configs/planner/boundaries/budgets. Require every seed's command sequence and exported game-state sequence (ignoring only wire timestamps/trace metadata), every entry hash/prefix, and preparation outcome identical to E133 v1. Record the refreshed bank separately as v2 with new dependency hashes; never overwrite v1. No substitutions. Maximum 10-minute validation batch, 8 workers for the cohort.
3. Run focused PPO/reset/provenance synthetic checks. Actual engine/draw/reward correctness in native save paths is re-certified separately by E133/E134 under the new hashes; E135 does not relabel earlier native failures.

## Gate and integration

Merge the ABI/provenance compatibility fix into the pending E134/E133 branch only if the frozen failure is resolved with exact pre-error states and three exact new-path replays, all 264 preparation histories/entries match, game DLL hashes are unchanged, and trace audits pass. Otherwise stop and retain the failure. No Godot/Steam global installation changes; proprietary files local ignored.

E133 v2 amendment, before retraining: keep all samples, model, learning settings, learner seeds, episode/work budgets and selection/test gates unchanged; use the separately recorded E135 adapter/stub hashes and refreshed identical bank, rerun per-entry certification, then E134 routing for any native-incompatible entries. Fail closed on any remaining real engine error. Training remains stopped until these gates pass. Record every added preparation/certification batch separately; do not retroactively claim the original 30-minute certification budget included new experiments.

## ABI build and frozen-case result v1

Implementation/test SHA `232caa3`. Additive source patch applied only to the ignored Godot stub Core.cs, local pinned SDK build succeeded (0 errors; nine warnings, including existing member-hiding warnings and new guarded base CallDeferred hiding). 22 focused synthetic tests passed (14 PPO/sampling + 4 fallback proof + 4 research restore).

The exact real failure prefix and four pre-error actions retained every observed hash. The formerly failing end_turn now advances round 1→2, Byrdonis HP 83→78, Rolling Boulder Amount 5→10, verifying the original unpowered 5 damage and +5 scaling. Neither unsupported visual method was invoked (they deliberately throw). The unchanged planner continued to legitimate battle clear; three independent complete-path replays matched all transitions/outcomes. Five source/current trace bundles audited. Case validation took 26.270 s; this one case is compatibility evidence, not a win-rate measurement.

```sh
git -C vendor/sts2-cli apply ../../patches/headless-zzzzzz-godot-abi.patch
.tools/dotnet/dotnet build vendor/sts2-cli/src/Sts2Headless/Sts2Headless.csproj --no-restore -v:q
python3 scripts/validate_godot_abi_e135.py case --output artifacts/runs/e135-case-v1.json
```

The original v1 error evidence and runtime backup remain unchanged. Next: recollect and compare all 264 preselected preparation histories before accepting an engine-version migration. PR #255 attachment was attempted; the app's 100-identity limit rejected it.

## Complete preparation regression and decision

Recollection ran at `66798bd`; comparison and the additional stub-provenance check ran at `9fedcf0`. All **264** fixed seed histories, **23,498** canonical command/state pairs and **1,460** battle entries matched the original bank exactly. Both proprietary game DLLs stayed byte-identical. All **528** old/new raw trace bundles passed audit. The refreshed bank is `experiments/E133/fixtures-v2.json`; v1 remains intact. The new provenance test rejects a changed Godot stub hash (5 restore tests pass; 23 focused tests across the three modules).

```sh
python3 scripts/retrain_ppo_e133.py freeze --output artifacts/runs/e133-fixtures-v2.json
python3 scripts/validate_godot_abi_e135.py compare-bank --new-bank artifacts/runs/e133-fixtures-v2.json --output artifacts/runs/e135-preparation-equivalence-v1.json
python3 -m unittest tests.test_research_restore
```

**Merge:** the frozen failure, original mechanic, three continuation replays, full preparation regression and provenance gates passed. Retain the guarded ABI addition. This proves compatibility only for the tested paths; native save fidelity and broader PPO policy paths remain separate gates. E133 must recertify under all four new runtime hashes before training.
