## Hypothesis
The E106-patched STS2-Agent on public v0.107.1 can let an AI controller operate only the local Ironclad throughout a real Steam co-op run while preserving every action and peer transition in trace. A fresh-state local-player gate plus explicit handling of shared waiting states should prevent the single-player controller from acting on peers or sending stale actions.

## Baseline and fixed inputs
Existing E109 proves only a Steam lobby and MCP read. E108 asymmetric peer experiment is still unexecuted. This is an exploratory, unpaired visible run; no causal win-rate comparison is claimed. The preexisting live run is `32ASTF9N6E`, four players (Ironclad, Regent, Ironclad, Defect), local Ironclad, A0, Steam client, at floor-1 Neow before any AI action. The seed is whatever the legitimate live host selected; record it if the MCP exposes it. Game v0.107.1/build 23811903, E106 adapter hashes from E109, main baseline SHA `1cf95b6`. Use the already configured Jev, task-mediated Astra planning when needed, and the E050 read-only overlay on Built-in Display. No player identifiers or chat content in public results.

## Decision rule and boundaries
First establish exactly one local controller writer and verify local-player ownership, each accepted action, and fresh hand/target indices. Stop on GAME_OVER, explicit user stop, ownership ambiguity, uncertain action delivery, unsupported shared choice without an observed safe local action, or a three-hour/$3 Jev/2000-action cap. Do not resend uncertain actions. Do not alter HP, rewards, victory, game DLL, network checks or friends' clients. Preserve all partial runs, failures, and trace hashes. Report compatibility, progress/floor, and win/defeat separately; a genuine win requires the game's victory state. Adapt strategy only from current state and record each change and why. Peer-controlled actions remain human-owned. The old overlay must be pinned to this run so historical traces never appear as live decisions.

## First live segment: observed failure

Tested gameplay SHA `1b64546fe2289ceecc7f91597a62b5ba4efedba7`, clean at launch. Game v0.107.1 and E106 adapter package were the E109 installation. Jev was configured as `typesafe/jev-1.13`; the first segment made two charged requests. The read-only E050 overlay source was `d800be43c2510a95912d7b29a573044a125226a6`, copied outside the repository and launched on Built-in Retina Display (`--screen 1 --opacity 0.78 --game-run-id 32ASTF9N6E`). The game had already advanced under human/peer play to floor 2 before AI control began. It was a four-player Steam client run with one local Ironclad; the actual seed was not exposed in the captured state.

```bash
python3 -m unittest discover -s tests -q
python3 -m rsi.campaign --expected-run-id 32ASTF9N6E \
  --require-local-multiplayer --expected-player-count 4 --execute \
  --combat-policy retaliate --auto-combat-selections --guard-exhaust-selection \
  --letter-opener-plan --pause-on-danger --danger-hp 20 --review-funded-shop \
  --max-actions 200 --max-seconds 900 --max-usd 0.20 \
  --output artifacts/runs/E110/segment01.json
```

151 unit tests passed. The controller accepted five local actions in 3.153 seconds: an event choice, a deck-card selection, event proceed, then two attempts to select the only map node. Both map actions returned `completed` from the adapter, but immediate and subsequent raw states still showed floor 3 map row 2, `local_vote=null`, `vote_count=0`, no peer votes and no change of screen. The pre-existing repeated-action guard stopped before a third send. Two Jev requests cost $0.000357714; there were zero explicit rejections or uncertain transport deliveries. Raw trace SHA-256: `4566b5fd934e764fd7a004dfd4028dfc672ae4193415ba578eab4698bf626ebb` (ignored local trace). [Sanitized result](result.json) has the complete compact outcome.

After the controller had stopped, a fresh MCP read and visible game inspection found the main-menu "choose a friend" multiplayer page with no friend currently playing. We cannot attribute the lobby exit to the map calls from the available evidence. No victory or later-floor result is claimed. The next independent map-vote experiment must ensure peer readiness and require observed vote/transition acknowledgement before any subsequent map action. This E110 segment establishes local ownership and event/card-selection compatibility only; multiplayer route progression remains unresolved.
