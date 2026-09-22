# Milestone 1 — auditable experiments and visible MCP control

Status: reached; game stopped at the reward screen for user acceptance.

The private repository records each experiment as an atomic issue, implementation/result commits, a separate PR, result comments and an evidence-based merge/close decision. `.agents/skills/sts2-experiment/SKILL.md` carries the repeatable workflow. The standalone Python controller runs the game/Jev loop; Astra reviews compact results and failure traces rather than making each action.

| Experiment | Observed result | Decision |
|---|---|---|
| E000 / PR #10 | Experiment protocol and reusable project skill | Merged |
| E001 / PR #11 | All five characters completed an A10 opening battle on the pinned headless engine | Merged compatibility setup |
| E002 / PR #12 | Independent budgeted Jev runner with complete traces; initial tactical comparison did not favor Jev | Merged infrastructure |
| E003 / PR #13 | 40 battles, 0 execution errors, 10 matched states across four policies; features failed the predefined promotion rule | Closed without merge |
| E008 / PR #14 | Native MCP visible combat completed; failure, fix and continuation all preserved; stopped at reward | Integration milestone |

E003 mean net HP loss: first-playable 11.1, numerical greedy 5.6, raw Jev 8.5, computed-context Jev 7.3. Features versus raw Jev: 1 better, 7 ties, 2 worse. The negative experiment and its 40 compressed traces remain on [PR #13](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/13). These are first-battle exploratory outcomes, not full-run win rates.

E008: existing Ironclad A0 floor-3 battle, 80 HP to 74 HP after victory, 14 accepted actions, 16 Jev requests, $0.002566410. One initial request was explicitly rejected before execution; the process stopped, the failure was committed, and a separate fix commit preceded the continuation. Both segments are in [the experiment report](../experiments/E008/README.md), along with raw compressed traces and native log corroboration.

Remaining work includes simulator fidelity/replay, stronger deterministic planning, strategy metadata, selective Astra escalation, longer battles and full-run evaluation across characters/high ascension. Observed weaknesses generated separate E009/E010 issues. No next experiment or further game action starts before this acceptance boundary is released.

## Reproduction entry points

```sh
python3 scripts/setup_headless.py
python3 -m unittest discover -s tests -v
python3 -m rsi.run --help
python3 -m rsi.live --help
```

The live controller defaults to read-only. Explicit execution requires the current live run ID and a combat state; the recorded demonstration command is not meant to replay an already-completed reward state. `.env` must contain `OPENROUTER_RSI_JEV_KEY`; it and proprietary game binaries remain ignored. The Codex MCP entry uses `http://127.0.0.1:8080/mcp`.
