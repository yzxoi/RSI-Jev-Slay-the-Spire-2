# E091: state-bound Astra Boss opening directives

Issue: [#174](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/174). Predecessor [E090](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/173) was closed: free-text plans yielded one genuine Boss clear in four selected failed entries, below its two-clear gate. This independent issue tests the narrower mechanism of executing a typed opener. E090's frozen fixture and plan implementation are cherry-picked here so the evaluator is runnable from main; that does not promote the E090 result.

Hypothesis: naming an opening potion and, for Duplicator, the exact next card/target as semantic IDs/names will cause intended resources to be executed from freshly observed legal actions, leading to at least one additional Boss clear versus a fresh free-text continuation. Ambiguous or illegal directives fail closed. The controller still delegates subsequent turn-openers and other decisions to Jev/planner.

Frozen inputs: four E089 Ascension 10 Act 1 Boss entry prefixes and hashes in `../E090/fixtures.json`, with the E090 free-text plans in `../E090/plans.json`. Treatment adds `plans.json` directives written before outcome evaluation: Ironclad Strength Potion; Silent Power Potion; Regent Duplicator then Astral Pulse; Necrobinder Duplicator then No Escape on Kin Priest. Both arms replay every exact entry, then stop at a real Boss-room exit. Two workers; up to 2,000 decisions/300 seconds per continuation; shared ceiling 1,000 Jev calls/$0.50. `python3 -m scripts.evaluate_boss_directive_e091` is the fixed command. Tests should pass before evaluation.

Gate: eight of eight entries, trace hashes, selected action legality, room boundaries and potion budgets valid; every treatment directive executed exactly once, with no stalls. Treatment must clear at least two of four Bosses and at least one more than fresh free-text control. Otherwise close without merging. This selected-after-failure four-case pilot tests mechanics, not full-run win rate; later RNG and action divergence limit paired causal inference. No HP, reward, RNG, victory or health edit is permitted. Record exact tested SHA, versions, outcomes and limitations after execution.

## Evaluation and decision

Tested implementation SHA `e3bb1438ec8494b1bf19d9176f5b9ca7f4ce9075` after 117 unit tests passed. Exact command: `python3 -m scripts.evaluate_boss_directive_e091 > artifacts/runs/e091-eval-stdout.log 2>&1`. The original game DLL SHA-256 was `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`; headless assembly, dependency hashes, plan/fixture hashes, exact configurations, all eight raw trace hashes and complete per-run outcomes are in [result.json](result.json).

All eight exact entry hashes, eight plan attachments, eight Boss-room boundaries, eight trace hashes, action legality, scope and potion budgets verified. Four of four typed opener sequences executed exactly once; zero stalls and zero uncertain calls. Across both arms there were 63 attempted Jev calls and $0.013354908 provider-reported/budgeted spend.

| Character, Boss | Free-text control | Typed opener | Last observed enemy HP, control → typed |
| --- | --- | --- | --- |
| Ironclad, Ceremonial Beast | **Boss clear** | **Boss clear** | 5 → 5 |
| Silent, Vantom | defeat | defeat | 98 → 77 |
| Regent, Kin Priest | defeat | defeat | 248 → 211 total |
| Necrobinder, Kin Priest | defeat | defeat | 199 → 199 total |

The typed policy spent Ironclad's Strength Potion, Silent's Power Potion, Regent's Duplicator before Astral Pulse, and Necrobinder's Duplicator before No Escape on Kin Priest. Silent's potion and Regent's duplicated AoE reduced remaining enemy HP without preventing defeat. Necrobinder accumulated 77 Doom on the Priest by round 7 but the Priest still had 169 HP while the player fell to 3 HP; the prescribed combo did not solve the survival/damage clock. These HP figures are the final before-action observations, not an estimate of the counterfactual damage effect. Boss-room clears do not constitute complete-run victories.

**Close without merging.** Treatment cleared one of four Bosses, equal to fresh control, below both preregistered gates. This isolates a real bottleneck beyond instruction delivery: choosing a legal opener and consuming a resource did not generally supply enough damage, scaling or defense for these Act 1 Boss fights. The cherry-picked E090 replay tooling and E091 failed attempt remain accessible on this closed branch; neither policy should be promoted to full runs on this evidence.
