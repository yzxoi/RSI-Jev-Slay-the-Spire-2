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
