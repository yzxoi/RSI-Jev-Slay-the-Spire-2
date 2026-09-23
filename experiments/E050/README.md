# E050 — Live read-only Jev/Astra decision window

Issue [#93](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/93).

Hypothesis: an incremental projection of the existing append-only native traces can make decisions inspectable during real play without another game writer, model call, or change to the control policy. This is an observability experiment; it makes no win-rate claim.

The practical baseline is manually tailing `decisions.jsonl`. It has exact evidence but requires reading deeply nested raw records, does not associate Jev probabilities with option names, and does not follow successive controller segments as one game run.

Fixed validation inputs from the real Ironclad A0 game run `LYU69TR2VY8F`:

| Case | Ignored local trace SHA-256 | Expected evidence |
| --- | --- | --- |
| Final room | `6d0cce78861d89611b0c22c31f81ec66a47afa89cc6fdb5c1cd7ecd43c7759e9` | Room plan, Jev choice distribution/confidence, accepted actions, victory |
| Astra escalation | `da7dd802631a3cc3b18edd1e96275a24ca3af212c9ec940b62e78e408882a055` | `low_hp_before_spending_energy` request, no invented choice confidence |
| Summary advance | `3113046deb0a07798be2c938df9f58c4cdb6a8d6cce881094d7b24fa17157265` | State-bound Astra action and verified summary |

Game v0.111.0, STS2-Agent mod v0.15.0. Also test synthetic partial writes, trace switching, missing confidence, and HTML injection. The monitor must bind to loopback, expose only a compact projection, and never call MCP or the model. Pass criterion: tests pass, fixed traces project to their recorded choices/escalation/outcome, and a visible small window updates during replay. Raw traces stay ignored; publish compact checks and hashes. Failure means close the PR with findings.

Implementation, tested SHA, exact commands, observations, limitations, and decision will be appended after evaluation.

User-directed presentation change before the next iteration: render the same read-only projection in a macOS AppKit overlay, default 410×490 points, 0.84 opacity, floating across Spaces and click-through over the game's upper-right display area. The browser window remains useful for interactive history and replay. The overlay must be visually inspected over the actual game victory window, with no native game action issued during validation. The same fixed traces and evidence rule still apply; this is a presentation iteration of E050, not a gameplay-policy experiment.

First native launch at tested SHA `c5233fd7d864117cad2432182e33e608c6c6602f` used `python3 -m rsi.overlay --replay-trace artifacts/runs/9836b6e7-6e37-411f-a31d-314aa70c78c0/decisions.jsonl --replay-interval 0.7 --opacity 0.78`. It exited before creating a window: PyObjC's AppKit NSRect bridge rejected flat four-number tuples (`ValueError: depythonifying struct of 2 members, got tuple of 4`). This is a presentation compatibility failure, with zero game/model actions. Next iteration uses nested `(origin, size)` tuples for every AppKit rectangle.
