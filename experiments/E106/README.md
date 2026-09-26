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
