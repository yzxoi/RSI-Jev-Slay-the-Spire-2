## Hypothesis
The E106 stable adapter can load in the user's normal Steam-on v0.107.1 installation and reach a genuine Steam-hosted multiplayer lobby.

## Authorized boundary
The user now explicitly requests launching the daily game and trying multiplayer. Install the already-tested adapter reversibly, launch the normal visible game with Steam, and open/host a multiplayer lobby. Stop at the lobby, unready. Do not invite/message friends, load a previous co-op run, enable autoplay, launch an AI companion, or start combat. This is a narrower check than E108's asymmetric-peer synchronization experiment.

## Fixed inputs and baseline
Steam public v0.107.1/build 23811903, ARM64 game DLL e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18. Use exactly the DLL/PCK/manifest hashes in E106/results.json. Baseline E106 passed isolated Steam-off main-menu MCP; Steam-on daily-profile startup is untested. Seeds/characters/ascension are not evaluation inputs because no run starts. Zero model calls.

## Decision rule
Pass this bounded smoke if the normal game reports v0.107.1 and ready, reaches a real Steam multiplayer host lobby, and MCP reads local-player/lobby state without runtime API errors. A one-player lobby is not peer connectivity or completed multiplayer evidence. Preserve backups and private raw logs/screens; publish only sanitized outcomes and hashes. Do not edit game DLLs, saves, stats, or network handshakes. Leave the game visible at the boundary for the user.

## Result (2026-09-26)

**Passed this bounded smoke.** Normal Steam public v0.107.1 launches visibly with the E106 adapter, native MCP stays healthy, and the game's own Multiplayer → Create → Standard path reaches a Steam-hosted character-select lobby. UI shows the invite button and one local player; HTTP and MCP agree on multiplayer mode, Host, 1/4 players, local player unready. Native game log records SteamHost initialization. Autoplay remains paused, session requests 0. The game is left running at this boundary for the user; nobody was invited and no run was started.

Implementation/test SHA: `bebf0a8` (installer and preregistered boundary). Adapter binaries match every hash in E106/results.json. No game assembly was modified. The installer copied three verified mod files to `SlayTheSpire2.app/Contents/MacOS/mods/STS2AIAgent/`, backed up the Steam profile tree and agent settings under ignored `artifacts/private/E109-install/`, and did not edit settings. All 37 pre-existing profile files still match the backup at the final read.

Executed installation:

```bash
python3 experiments/E109/install_stable.py \
  --game-app '/Users/yzxoi/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app' \
  --package vendor/STS2-Agent-stable-probe/build/mods/STS2AIAgent \
  --record artifacts/private/E109-install
open 'steam://rungameid/2868840'
```

The CUA game window was selected by the full normal application path (the isolated E106 copy shares its bundle ID). Screenshot-based clicks opened Multiplayer, Create and Standard; each was followed by fresh UI observation. `GET /health`, `GET /state`, native MCP initialize and `get_game_state` were captured before/after in `artifacts/runs/E109/`; compact sanitized findings and hashes are in `results.json`. The native MCP remains at the pre-existing Codex endpoint `http://127.0.0.1:8080/mcp`.

Known limitation: the log contains missing controller InputMap action names (such as `controller_r_stick_down`). Mouse navigation works; this smoke does not test controller support or establish the cause of those messages. A one-player Steam lobby does not prove a friend can join, differing mod sets are compatible in practice, or combat stays synchronized. Those remain E108/#207; single-player actions remain E107/#206.

**Decision:** merge the reproducible installer and bounded live evidence. Keep the user-requested mod installed and the game at the unready lobby. Do not mark broader multiplayer compatibility complete. Rollback is to close the game and move only this newly created manual mod directory outside `mods`; profile backups are recovery material, not something to overwrite newer progress with.
