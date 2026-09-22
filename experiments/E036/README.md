E033 held-out Silent a0_e033_hold_002 planned (ecb6721d-a87e-4aac-9d06-c67203c0af55) triggers Tools of the Trade discard at the next turn start. Headless DoEndTurn interprets this legitimate pending selection as a deadlock, cancels/retries, then returns a forced game_over. The evaluator correctly reports error, not defeat.

Hypothesis: bounded read-only/pump waiting must stop on pending card/reward/bundle selection as well as play phase/combat completion. Remove end-turn cancellation/re-execution fallback; timeout is an adapter error, never a fabricated defeat.

Freeze exact failed wire prefix through that end_turn. Require card_select with the original6-card options, select a legal card, resume the same new turn without replaying EndTurn or applying enemy damage twice. Also replay E018 Particle Wall and Dense Vegetation and E034 Amalgamator prefixes. Commit patch before build; do not change shared binaries while E033 held-out processes run. Separate compatibility from policy strength; preserve the failed20-run batch.

Additional regression after diagnosis: the same held-out batch has Regent a0_e033_hold_002 planned stopping on a 25-card turn-start prompt at round10. Freeze its failed prefix and require that real prompt, then one legal choice must resume round10 with unchangedHP. This extends adapter coverage; the failed held-out outcome remains an error.
