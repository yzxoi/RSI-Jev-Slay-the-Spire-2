# E019 — Native explicit reward skip

Issue #33. Baseline E017 attempt4-s009 reopened the card reward after explicit skip. Scope skip memory to run+floor, exclude that Card reward from manual claims, then invoke the MCP reward drain which respects its own skip scope. Continue manually claiming other rewards so card selection stays explicit. Fixed native check: MDGN86P6N6BF floor6, skip same offer, unchanged deck, reach next room. Also verify a later normal card claim. No game edits. Commit before execution, retain before/after traces and outcomes.
