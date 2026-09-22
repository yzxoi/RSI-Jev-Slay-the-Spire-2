# E008 — Visible native-MCP combat milestone

Issue #9. Hypothesis: the merged raw Jev controller can operate the real visible game through MCP tools, record each transition and stop before choosing post-combat rewards.

Selected existing run: `9JKXVG5BK1D8`, Ironclad, ascension 0, floor 3, first turn against Nibbit (46 HP), player 80/80. This user-owned live state is a transport demonstration, not part of the A10 strength evaluation. No game values are edited.

Baseline: prior read-only initialization. Maximum 80 actions / 240 seconds / 100 Jev calls / $0.15. One local writer lock, built-in autoplay must remain off, and state/action indices are checked again after inference. Uncertain action delivery stops the controller instead of replaying the action. Unsupported overlays or lethal end-turn choices stop for expert attention.

Iteration 1: add direct JSON-RPC MCP transport, live candidate adapter, readiness/identity guards and a reward-boundary stop. Reuse the merged Jev chooser; E003's rejected computed-context experiment is not promoted here.

Decision rule: merge on a verified real combat-to-reward transition, complete trace audit and no repeated/stale action. Then stop for user acceptance. Full-run automation and high-ascension strength remain future milestones.

```sh
python3 -m unittest discover -s tests -v
python3 -m rsi.live --expected-run-id 9JKXVG5BK1D8 --output experiments/E008/preflight-v1.json
python3 -m rsi.live --expected-run-id 9JKXVG5BK1D8 --execute --output experiments/E008/results-v1.json
```
