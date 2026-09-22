E024 first result exposed a reporting hazard: headless context.floor resets at Act2 (Ironclad planned reaches Act2 floor6, cautious dies Act1 floor17). Comparing raw floor reverses progress.

Audit every committed full-run report for multi-act results; define ordered progress as (victory, act, floor), report win count, act distribution and paired progress separately. Avoid inventing a global-floor offset when act length differs. Recompute prior conclusions where any act2+ runs appear; preserve original summaries and add explicit correction files/comments. No game execution or policy changes. Validation uses actual cross-act pair plus synthetic control/ties.

Issue #45. Test source is existing completed report bytes, not new runs. Preserve source SHA256 and repository-relative report path.

At 8d3c716, 19 tests pass. Audited 25 distinct completed full-run report versions. Cross-act rows occur in E014 development-v1 (planned reaches Act2 twice) and E020 heldout-v1 (advised Ironclad reaches Act2 floor10). Their raw mean-floor summaries understated progress and must not be interpreted as overall reach. Paired ordered comparisons are retained. Neither changes its final close decision: E014 raw Jev remained negative on corrected heldout; E020 corrected matched evaluation tied all 15 pairs. E024 will use act-aware comparison from the outset.
