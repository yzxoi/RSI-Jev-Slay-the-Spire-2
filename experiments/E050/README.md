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

Second native launch at tested SHA `1ae2e386f3eef2cd45fd3fe4799bfa16c636d507` created a 410×490 point, 0.78-opacity, click-through AppKit panel and replayed the fixed floor-48 trace. Visual inspection found a layout defect: with an Astra plan visible, the fifth candidate row overlapped the plan card and footer. The next iteration reserves space for the plan, shows the top three options including the selected one, and displays the full option count in the heading. No game/model action occurred in this visual test.

At tested SHA `98706f8625f54de573a9a5d4ca7bea80f253aa6b`, the repaired replay panel showed the actual Jev `Perfected Strike` choice, confidence 84%, and top candidate probabilities 86%/3%/3%; a separate screenshot showed the Astra-bound opener with confidence absent and no overlap. A derived local trace containing rows 0–53 of the fixed final-room trace (SHA-256 `efba26ec4c905f1d853d2b058d60defe6aad295cdd9619a7364fc5e77486145c`) was used to hold the Jev frame; this derived replay is **not** another native game run. Switching the bundle to `--game-run-id LYU69TR2VY8F` then exposed a source-selection defect: the synthetic replay directory under `artifacts/runs/` had a newer mtime and a copied native manifest, so it was falsely shown as LIVE. The next iteration restricts automatic discovery to UUID-named controller trace directories; explicit replay paths remain unrestricted. The source game and model were not touched.

At tested SHA `fa91326ea8c2cd7444b291f5f753c49d5cd3c2fb`, the unit suite passed 72 tests and the auto follower selected real segment `b1230cff-92f7-4c47-81ec-a6330950d181`, not the derived replay. The live overlay correctly lacked Jev confidence for the Astra-only summary action, but two display ambiguities remained: a finished trace still carried the LIVE badge, and the scripted victory screen's HP 0 looked like a defeat. The next iteration marks trace inactivity after 60 seconds and surfaces `game_over.is_victory` directly; it also abbreviates long expert explanations into action labels while preserving the reason in the browser view.

Final tested implementation SHA: `cee3ff629b648673ed3b8feb7552821d1f731051`. `python3 -m unittest discover -s tests -q` passed 73 tests. Read-only replay of the three preregistered native traces reproduced their exact hashes, Jev 0.84 confidence and 0.86 selected-action probability, Astra's `low_hp_before_spending_energy` escalation without a fabricated confidence, and the victory summary's `is_victory=true`. `python3 -m rsi.overlay --replay-trace artifacts/runs/e050-jev-replay/decisions.jsonl --replay-interval 0.08 --opacity 0.78` drove the visual Jev demonstration from a clearly derived local prefix; `python3 -m rsi.overlay --game-run-id LYU69TR2VY8F --opacity 0.78` showed the true latest UUID native segment, now labelled “等待新决策” and “胜利”. Both commands only read traces. The AppKit panel was visibly 410×490 points with no overlapping option and plan rows. The browser monitor remains available through `python3 -m rsi.monitor --game-run-id LYU69TR2VY8F --open`.

Runtime: Python 3.13.5, macOS 26.6.2, PyObjC Cocoa 12.2.1, game v0.111.0, STS2-Agent mod v0.15.0, recorded Jev response model `typesafe/jev-1.13-20260917`. Machine-readable checks and trace hashes are in [result.json](result.json); raw records remain ignored locally. No new native game action, model request, battle outcome, or win-rate observation was produced.

Decision: publish the PR for placement review and keep it open. During this evaluation the game had moved to the main menu, so a composited capture over the earlier victory screen and an input test of click-through over active combat were not available. AppKit is configured with floating/full-screen auxiliary behavior and click-through, and the panel itself was inspected in both replay and live-follow modes; final positioning over an active fullscreen game needs an on-screen acceptance pass before merge.

User-directed live-play refinement: the overlay was moved to the Built-in
Retina Display using its observed AppKit screen index 1; the launcher retained
`--opacity 0.78 --screen 1`. During E051's fresh A0 native run, the overlay
visibly followed run `F1GR9R0YXCCC`, including the first combat's Automatic
actions. The user observed that missing confidence and probability values
appeared as repeated `—` glyphs. This was expected for computed/automatic
actions, but the UI failed to explain it. When the E051 controller stopped on
floor 5 after a Jev DNS failure (63 accepted actions; raw trace SHA-256
`fd7dd8115ab2c9cc6264d906616bfbf30f75c9de919b56dd37e62995ec214b40`),
the overlay also showed the previous accepted action instead of the failed
pending request. This is an observability defect, not a new game-policy result.
The fixed evaluation input for this presentation iteration is that exact
immutable native segment. Accept if pending Jev, successful Jev, automatic,
computed and failed Jev states have distinguishable truthful labels, missing
probabilities never look like zero confidence, the failed request supersedes
the stale action, and the 75-test suite plus visual inspection pass. No game
action or model call is needed for this UI evaluation.

At tested SHA `712dfb8`, a read-only screenshot of the exact stopped native
segment showed the failed Jev request with “控制已停 / 请求失败”, HP82/91 on floor5
turn3, the unexecuted candidate set and no fake probability. A derived local
prefix through trace sequence 1491 showed the previous Computed end turn
without dashes, using a checkmark for the selected action; it is not another
game action. Visual review found redundant English `Computed` plus Chinese
“数值规划” and no explicit “not applicable” label. The next presentation-only
iteration translates the source and uses “Jev 概率 / 不适用” for non-Jev actions.

Final presentation iteration at tested SHA
`d80cb60c58220caeee04607eafe62c8f77ffa754`: 75 unit tests passed with
`python3 -m unittest discover -s tests -q`. Visual inspection of read-only
prefixes of the E051 trace confirmed two distinct states: a Computed accepted
action is labelled “数值规划 / Jev 概率不适用” with a checkmark instead of `—`; an
in-flight model request says “Jev 正在评估 / 等待响应” and does not imply 0%
confidence. The full native trace shows “Jev 请求失败 / 控制已停” and the unexecuted
candidate set rather than the prior accepted action. The launcher was returned
to live automatic trace following on Built-in Retina Display, opacity 0.78.
`result.json` records trace hashes and the source run's separate 63-action
gameplay outcome. No game or model action was issued to evaluate this UI fix.
Keep PR #94 open for user review; click-through against an active fullscreen
game input has not been independently verified.
