# E083 — source-audited deck jobs research

Issue: [#158](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/158). Baseline: `origin/main` at `8ea843d434a64fedd3247a2dafd6f6092fab8293`, whose `rsi/full.py` has a short generic STRATEGY prompt. E083 changes no gameplay code.

Hypothesis: a versioned “deck jobs” checklist can translate external STS2 strategy and local trace observations into testable reward/path questions without hard-coding card tiers. The deliverable is a research memo, not a measured policy improvement.

Frozen inputs: Jorbs's jobs article (2026-03-06), Baalorlord's deckbuilding concepts (2026-03-04), Untapped's deckbuilding, map, combat, and five character guides, all accessed 2026-09-24; game version v0.111.0 as reported in E081; E081 Ironclad A1 run `8X3876DS2JL4` segment-01 trace SHA-256 `e0fd99e72429c47b2abf1933cc1ef5e11df8fd2436b80ee16fdf6aff89ecd420`, card rewards on floors 2, 3, 5, 8 and 9. Raw traces stay under ignored `artifacts/runs/`.

Decision rule: merge the memo only if cited sources support adjacent claims, the five observed rewards match the hashed local trace, character mechanics are constraints rather than required archetypes, and the follow-up experiment separates offline decision changes from battle and full-run outcomes. Revise failed audit points before merging. This work does not touch the paused game.

## Iteration 1

Reason: existing strategic text names broad priorities but does not expose an auditable threat ledger or separate resource throughput from card quality. The source review also found patch drift and conflicting fixed heuristics, so the memo uses versioned, conditional claims.

Implementation commit: pending. Audit results and exact tested SHA will be added in a separate commit after verification.
