# E154 — Guarded encounter ABI compatibility

Issue [#292](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/292). Dependent on E153; no policy optimization.

## Protocol before testing

E153 v1 contains90fixed natural runs,88defeats and2errors. Missing Node.GetIndex(bool) blocks original ReattachPower final-segment death; missing CanvasItem.SetVisible(bool) causes Crusher.AfterAddedToRoom JIT to fail before applying original BackAttackLeftPower and CrabRagePower. Decompiled original code shows these visual calls behind null guards. Add exact ABI signatures that throw if actually invoked. Both original/patched game DLLs must remain byte-identical. Add fail-closed stderr integrity detection, including asynchronous exceptions.

Rerun the same90E153seeds/configurations at max900s/8workers. Require all88unaffected histories exact, train-A0-011 exact through its pre-error state, and dev-A0-002 exact until original Crusher power initialization; that first semantic difference must be the missing original powers restored at the Kaiser Crab encounter. Subsequent outcomes may differ naturally and are compatibility evidence only. Independently replay both corrected complete paths, preserve all old errors and new outcomes, audit every trace. If any unresolved exception or unexplained difference remains, stop curriculum fitting. Trial.Accept visual null access remains known and separately unresolved if the corrected route reaches it. No substitute seeds.

Commands:
```sh
.tools/dotnet/dotnet build vendor/sts2-cli/src/Sts2Headless/Sts2Headless.csproj --no-restore -v:q
python3 scripts/train_curriculum_e153.py collect --plan experiments/E153/plan-v1.json --output artifacts/runs/e153-collection-v2.json
python3 scripts/validate_encounter_abi_e154.py --collection artifacts/runs/e153-collection-v2.json --output artifacts/runs/e154-validation-v1.json
```

Initial ilspy invocation needed DOTNET_ROLL_FORWARD=Major for .NET8 target under .NET9. An edit assertion stopped before changing UI.cs; corrected before testing. Both command failures preserved in task history; no game runs used the partial edit. Raw decompilation/binary backups remain ignored locally.
