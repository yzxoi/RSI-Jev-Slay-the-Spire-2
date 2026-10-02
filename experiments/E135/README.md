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
