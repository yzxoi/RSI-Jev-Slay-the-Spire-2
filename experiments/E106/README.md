## Objective
Expose the existing STS2-Agent MCP on the user's installed Steam public branch without requiring friends to switch to beta. Distinguish compilation, mod loading, MCP behavior, and Steam multiplayer compatibility.

## Hypothesis and baseline
Upstream STS2-Agent v0.16.2 (829ba230e79839ea26dcb9749bf93f268adff697) targets game >=0.111.0; the installed public build is v0.107.1, Steam build 23811903. A bounded adapter against actual stable assemblies may preserve its MCP contract. First compare an unmodified upstream build against stable; do not merely lower the manifest minimum.

## Fixed inputs and budget
- macOS ARM64, installed original sts2.dll SHA256 e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18.
- SDK 9.0.318; upstream pinned commit above.
- Compile and offline API inspection only initially; no model calls, seeds, or win-rate claims.
- Do not change Steam branch, deploy into the installation, or touch real saves during this probe.

## Decision rule
Record exact source/API mismatches and multiplayer handshake requirements. If changes are bounded and semantic mappings are supported by the stable engine, produce a reversible adapter and recompile. Otherwise retain a precise implementation proposal and failure evidence. Compilation alone does not establish gameplay or Steam co-op support. Keep any decompiled proprietary code/binaries private and ignored; publish only findings, original adapter code and hashes.

## Iteration 1: reveal stable API differences

Baseline experiment commit `ed66ecc`, upstream `829ba23`, SDK 9.0.318: direct Release build against the installed ARM64 game assemblies fails with CS0246 `StartRunLobbyPlayer`. The stable lobby exposes `MegaCrit.Sts2.Core.Entities.Multiplayer.LobbyPlayer`; replace this parameter type in an isolated upstream checkout, preserving the MCP payload. This first correction is only intended to reveal subsequent compilation diagnostics. Patch is derived from upstream AGPL-3.0 code and retains that license; no game implementation is published.

Local engine inspection confirms that v0.107.1 already has mod initialization, `affects_gameplay`, version checking and separate gameplay/non-gameplay mod lists. Its join flow rejects game version and gameplay-mod mismatches but allows non-gameplay mod differences with a warning. This is static inspection, not a Steam co-op test.

## Iteration 2: map documented stable semantics

Iteration 1 (`2f19839`) exposed two more compile errors. Stable `RunLobby.ConnectedPlayerIds` is the connected-player collection; stable `NPotionPopup` disables **both** use and discard when `Player.CanRemovePotions` is false. Map those APIs without weakening the potion gate. Additionally, stable `StartRunLobby` has public `MaxPlayers` with a private setter instead of `_maxPlayers`; use the property through the existing reflection registry so both reading and the upstream local-companion cap adjustment resolve consistently. Lower both manifests to 0.107.1 only alongside these source changes. This patch is specific to the fixed stable assembly, not a universal stable/beta binary.

Add an offline probe of the upstream reflection registry against the actual game assembly. It resolves metadata only and does not initialize a game, invoke game methods, or claim runtime MCP success.

## Iteration 3: isolated native smoke boundary

Tested adapter commit `62b00e9`: Release compile passed with zero warnings/errors; all 27 reflection registry entries resolved. Proceed to a bounded native smoke test: APFS-copy the installed application into ignored private artifacts, stage the adapted mod there only, launch with Steam disabled and a new numeric client ID `2026092606`, separate agent settings, no model credentials, MCP enabled and autoplay off. Stop after main-menu health/state/MCP reads (no embark, combat or rewards). Hash the existing Steam/default profile files before/after and leave the installed app untouched. This establishes only native startup and read APIs, not action compatibility or multiplayer.

## Result and decision (2026-09-26)

**Feasible: the adapted STS2-Agent v0.16.2 loads inside the actual stable v0.107.1 engine and serves native MCP.** This is an experimental stable-specific patch, not a certified production release.

| Check | Unmodified upstream | Stable adapter |
| --- | --- | --- |
| Direct compile | missing `StartRunLobbyPlayer`; iteration 1 then exposed 2 further API errors | 0 errors / 0 warnings |
| Offline registry resolution | 26/27; `_maxPlayers` missing | 27/27 |
| Native mod startup | not attempted with known incompatible source | `/health`: v0.107.1, ready, 27 checked / 0 missing |
| HTTP state / MCP state | not tested | both MAIN_MENU |
| MCP initialization / tools | not tested | successful; 16 tools listed |
| Existing profile / installed app integrity | read only | all existing profile and installed-app file hashes unchanged |
| Model calls | 0 | 0 |

The native application was a copy of the installed **real game**, with `--headless --force-steam off --clientId 2026092606`; it was **not** our old headless CLI simulator. No game or mod binary is committed. Raw evidence stays in the main checkout's ignored `artifacts/runs/E106/` and `artifacts/private/E106-native-smoke/`; hashes and sanitized outcomes are in `results.json`. The test process has stopped. Neither the user's Codex MCP endpoint nor the installed game was changed.

After SIGTERM, the mod stopped its HTTP/event services, then the engine logged unreferenced static-string errors and `libc++abi: terminating`. This occurred after successful MCP reads; clean graceful shutdown remains unverified. There was no full upstream regression-suite run. The mod still reports upstream version `0.16.2`; identify this experimental binary by the patch/build hashes, never by that version alone.

**Multiplayer conclusion:** static inspection of this installed stable assembly's `JoinFlow` verifies that game version and gameplay-mod lists must match, while non-gameplay mod differences are allowed with a warning. Upstream declares `affects_gameplay: false`, which the adapter preserves. This gives a plausible path for a local MCP player joining friends without requiring them to install the agent. Actual Steam matchmaking, model-ID hash equality, synchronization, control scope, disconnection/rejoin and asymmetric mod installation have **not** been tested. The upstream local dual-instance AI teammate is also not proof of Steam-friend compatibility. Do not bypass version/mod handshakes.

**Decision:** merge this feasibility experiment, original probe and source adapter into the research repository. Do not automatically install it or enable autoplay. Follow-up gates before relying on it: [stable single-player actions through the first reward (#206)](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/206); [asymmetric-mod local multiplayer synchronization and then a consented Steam-friend session (#207)](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/207).

## Reproduction

Issue: [#204](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/204). PR: [#205](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/205).

Source and adapter are fixed by `results.json`. `stable-compat.patch` is derived from [STS2-Agent](https://github.com/CharTyr/STS2-Agent/tree/829ba230e79839ea26dcb9749bf93f268adff697) and licensed **AGPL-3.0**; upstream's license applies to the combined source. Proprietary game binaries and decompiled implementations are never published.

The commands used are equivalent to the following from the main research checkout; `E106_DIR` points at this experiment in its worktree or merged checkout:

```bash
export STS2_DATA_DIR='/Users/yzxoi/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app/Contents/Resources/data_sts2_macos_arm64'
export PATH="$PWD/.tools/dotnet:$PATH"
E106_DIR='/Users/yzxoi/RSI-Jev-Slay-the-Spire-2-worktrees/RSI-Jev-Slay-the-Spire-2-e106/experiments/E106'

# Fresh checkout only; never apply over an unknown upstream revision.
git clone https://github.com/CharTyr/STS2-Agent.git vendor/STS2-Agent-stable-probe
git -C vendor/STS2-Agent-stable-probe checkout 829ba230e79839ea26dcb9749bf93f268adff697
git -C vendor/STS2-Agent-stable-probe apply "$E106_DIR/stable-compat.patch"
dotnet build vendor/STS2-Agent-stable-probe/STS2AIAgent/STS2AIAgent.csproj -c Release
dotnet run --project "$E106_DIR/MemberProbe" -- "$STS2_DATA_DIR" vendor/STS2-Agent-stable-probe/STS2AIAgent/Game/ReflectedGameMembers.cs
bash vendor/STS2-Agent-stable-probe/scripts/build-mod.sh --configuration Release --skip-install --data-dir "$STS2_DATA_DIR"
python3 "$E106_DIR/native_smoke.py" \
  --app '/Users/yzxoi/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app' \
  --staged-mod vendor/STS2-Agent-stable-probe/build/mods/STS2AIAgent \
  --output artifacts/private/E106-native-smoke \
  --client-id 2026092606 --port 18106
```

The baseline was the same direct build before applying the patch; the first-iteration patch is preserved in commit `2f19839`. Adapter/probe evaluation used `62b00e9`; the packaging/native smoke used `1091832`. SDK 9.0.318, runtime 9.0.20; game engine reports MegaDot 4.5.1.m.12. For another smoke attempt choose a **fresh output directory, numeric client ID and free port**; the script intentionally refuses to reuse an existing profile. All checks here used the installed ARM64 DLL hash stated above, not the historical CLI game DLL.
