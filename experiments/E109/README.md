## Hypothesis
The E106 stable adapter can load in the user's normal Steam-on v0.107.1 installation and reach a genuine Steam-hosted multiplayer lobby.

## Authorized boundary
The user now explicitly requests launching the daily game and trying multiplayer. Install the already-tested adapter reversibly, launch the normal visible game with Steam, and open/host a multiplayer lobby. Stop at the lobby, unready. Do not invite/message friends, load a previous co-op run, enable autoplay, launch an AI companion, or start combat. This is a narrower check than E108's asymmetric-peer synchronization experiment.

## Fixed inputs and baseline
Steam public v0.107.1/build 23811903, ARM64 game DLL e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18. Use exactly the DLL/PCK/manifest hashes in E106/results.json. Baseline E106 passed isolated Steam-off main-menu MCP; Steam-on daily-profile startup is untested. Seeds/characters/ascension are not evaluation inputs because no run starts. Zero model calls.

## Decision rule
Pass this bounded smoke if the normal game reports v0.107.1 and ready, reaches a real Steam multiplayer host lobby, and MCP reads local-player/lobby state without runtime API errors. A one-player lobby is not peer connectivity or completed multiplayer evidence. Preserve backups and private raw logs/screens; publish only sanitized outcomes and hashes. Do not edit game DLLs, saves, stats, or network handshakes. Leave the game visible at the boundary for the user.
