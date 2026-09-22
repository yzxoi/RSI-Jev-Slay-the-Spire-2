# E019 — Native explicit reward skip

Issue #33. Baseline E017 attempt4-s009 reopened the card reward after explicit skip. Scope skip memory to run+floor, exclude that Card reward from manual claims, then invoke the MCP reward drain which respects its own skip scope. Continue manually claiming other rewards so card selection stays explicit. Fixed native check: MDGN86P6N6BF floor6, skip same offer, unchanged deck, reach next room. Also verify a later normal card claim. No game edits. Commit before execution, retain before/after traces and outcomes.

Native execution at 0073500: explicit skip succeeded, deck exactly unchanged, next room REST floor7. Normal shop purchases Uppercut/Stone Armor/Shrug completed and gold correctly reduced from170 to6; smith selection and confirmation reached floor9. This is reward-lifecycle evidence, not a strength measurement. Continue to verify later card offer can be taken.
