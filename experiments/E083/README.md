# E083 — source-audited deck jobs research

Issue: [#158](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/158). Baseline: `origin/main` at `8ea843d434a64fedd3247a2dafd6f6092fab8293`, whose `rsi/full.py` has a short generic STRATEGY prompt. E083 changes no gameplay code.

Hypothesis: a versioned “deck jobs” checklist can translate external STS2 strategy and local trace observations into testable reward/path questions without hard-coding card tiers. The deliverable is a research memo, not a measured policy improvement.

Frozen inputs: Jorbs's jobs article (2026-03-06), Baalorlord's deckbuilding concepts (2026-03-04), Untapped's deckbuilding, map, combat, and five character guides, all accessed 2026-09-24; game version v0.111.0 as reported in E081; E081 Ironclad A1 run `8X3876DS2JL4` segment-01 trace SHA-256 `e0fd99e72429c47b2abf1933cc1ef5e11df8fd2436b80ee16fdf6aff89ecd420`, card rewards on floors 2, 3, 5, 8 and 9. Raw traces stay under ignored `artifacts/runs/`.

Decision rule: merge the memo only if cited sources support adjacent claims, the five observed rewards match the hashed local trace, character mechanics are constraints rather than required archetypes, and the follow-up experiment separates offline decision changes from battle and full-run outcomes. Revise failed audit points before merging. This work does not touch the paused game.

## Iteration 1

Reason: existing strategic text names broad priorities but does not expose an auditable threat ledger or separate resource throughput from card quality. The source review also found patch drift and conflicting fixed heuristics, so the memo uses versioned, conditional claims.

Implementation commits: `b214926` (memo), `7bf22bf` (trace-audit tool), `e367e37` (permanent E081 source link and typed-record proposal). No failed implementation was removed.

## Audit result

Tested SHA: `e367e3796a555f7623c6ea683ac809a33c7058d4`. Exact local command:

```sh
python3 experiments/E083/audit.py /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/artifacts/runs/af29b292-6afc-4c3e-b21c-4b2685371598/decisions.jsonl
```

The audit recomputed the ignored trace SHA-256, parsed every selected card reward, and compared its floor, full candidate IDs and chosen ID with the memo. All five rows matched on floors 2, 3, 5, 8 and 9. The eleven cited public strategy/patch pages were opened and the nearby claims checked against their text; the E081 checkpoint's pinned GitHub commit link resolved. `git diff --check` passed. Compact outcome: [result.json](result.json).

Game v0.111.0, mod v0.16.1 and Jev `typesafe/jev-1.13` describe the **source E081 run**, not E083 execution. E083 sent zero game actions and zero model requests. It did not conduct CLI simulation, causal reward replay, battle evaluation or a win-rate test. The A1 source run has no confirmed terminal result. Character guide examples can drift from beta card text; the current game state remains authoritative. A policy trial requires a new issue with frozen matched inputs and an explicit decision rule.
