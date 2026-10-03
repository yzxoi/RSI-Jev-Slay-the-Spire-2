# E158 — Preserve saved unknown-room odds on Map reconstruction

Issue [#304](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/304). Dependent on E157; no policy training.

## Frozen diagnosis and protocol

E157 has112/120matching loaded paths and8failures at two roots ofA0-002. A loaded Map/reward can match its original observation yet the future unknown node(2,13) changes from Raiders combat to Dense Vegetation. Private inspection of the original v0.111.0 methods finds that RunState.FromSerializable restores unknown-room odds, but the adapter's subsequent EnterAct→SetActInternal resets those odds to base. The original file contains accumulated monster/shop/treasure odds0.2/0.06/0.04. Restore the four serialized odds after reconstructing an already-visited Map. Do not edit saves, RNG, HP, deck, rewards, original/patched game DLLs or Godot stubs. The headless adapter assembly necessarily changes.

Before loaded recertification, replay all60 frozen E157 A full suffixes under the changed runtime via ordinary full-prefix starts. Require every earlier prefix, suffix response and final hash exact: normal start_run behavior must remain unchanged. Then twice replay every original native-save suffix in independent processes:120loaded paths. Native bytes/seed/ascension must remain original. Prospective snapshot metadata binds the candidate runtime only inside this validator; this is not relabeling E157's failed certificate. E157's8failures remain unchanged.

All30roots and180paths must pass before2 paired A/C restoration timings per root, alternating order by(index+repeat)%2.120timing paths total. Require no mismatch/error/cap/timeout, unchanged native files, complete evidence audit, paired median speedup>=2,Cp95<=Ap95. Budget900s wall/1800s aggregate parent+childCPU,4workers,90s full suffix/30s timing. No replacements. Only a passing new-runtime certificate can support a separately frozen E149 rerun; its seeds/actions/continuation streams and teacher gates remain unchanged. Final330 acceptance seeds unused.

```sh
.tools/dotnet/dotnet build vendor/sts2-cli/src/Sts2Headless/Sts2Headless.csproj --no-restore -v:q
python3 scripts/validate_map_odds_e158.py --output artifacts/runs/e158-validation-v1.json
```

Decompiled original game sources remain private under ignored artifacts/private. The public patch only modifies the open headless adapter to rehydrate existing serialized fields. The preceding E157 decompiler invocation without the local runtime override failed before inspection; using DOTNET_ROOT and DOTNET_ROLL_FORWARD=Major resolved it.

## Validation v1 / scoped reuse decision

Tested `ae67ae2df98099c4cc1f7ea24c89b71a9d62b349`. Build0errors/1warning. All60 ordinary full-prefix paths remain exact; all120loaded paths now match every expected response/final hash, including the8 formerly failing replays. All120paired timing paths restore the intended root. Native files, original/patched game DLLs and Godot stubs remain unchanged; only the adapter assembly changes.420bundles audit, no mismatch/error/cap. Validation231.122s/338.125CPU seconds.

Full-prefix median/p95=3.801/6.015s; Map+short-prefix=1.676/2.546s; median of60 paired speedup ratios=2.118x. Fidelity and scoped performance gates pass for all30exact roots/runtime. Merge this loading correction and certificate, allowing an explicitly frozen E149 recovery-only iteration. No neural policy, playing-strength or universal hidden-state-clone claim; E157old-runtime failure stays recorded.
