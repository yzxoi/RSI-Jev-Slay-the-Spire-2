# E023 — Sandpit survival rule

Issue #41. Baseline attempt4 died at floor33 while holding playable Frantic Escape. The native damage-only lethal flag missed enemy Sandpit expiry. Use cheapest legal Frantic Escape at Sandpit <=2 before ordinary combat planning. At <=1 with no legal escape, escalate before any energy is spent. Explicit state-bound Astra review may override (for example a verified kill). Do not alter HP, countdowns, cards, or past outcomes.

Evaluate every captured boss state from attempt4 s068; add controls for no escape, healthy countdown, and an unrelated encounter. Commit implementation before evaluation; record chosen actions and raw source hashes. Offline re-ranking does not prove an alternate win. Apply to a fresh full native run after verification. This is a narrow execution/survival correction, not a general high-ascension strength claim.

At f9aa261, all 21 unit tests pass and campaign syntax compiles. Offline replay records every captured pre-action boss state and chosen rule action. It selects legal escape before the original fatal energy spending and escalates when that opportunity has already been lost. This demonstrates hazard recognition only; the failed live run remains a defeat.
