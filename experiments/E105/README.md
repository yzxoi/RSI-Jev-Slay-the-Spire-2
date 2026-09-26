# E105 — nullable empty power-list compatibility

Issue #202. Fixed regression corpus: all four E104 iteration-1 failures caused by `player_powers: null`, recorded in inputs.json as arithmetic-relevant projections with full-state and source-trace hashes. Two Ironclad failures share the same state; this is compatibility coverage, not independent statistical evidence. The pinned exporter explicitly emits null for an empty power list (vendor/sts2-cli/src/Sts2Headless/RunSimulator.cs:2259).

First commit the recorded-input regression and show that main's arithmetic raises TypeError. Then change only nullable empty-list handling, commit, and require all four projections to match their equivalent empty-list previews, plus the existing suite. Preserve failures and code SHAs. Nonempty Plating behavior is covered by the existing E103 control tests. No model calls, engine branches, altered game values or victory claims; these are read-only unit checks.

Commands: `python3 -m unittest discover -s tests -p test_null_powers_e105.py -v` for the pre-fix reproduction; `python3 -m unittest discover -s tests -q` after the fix. Keep this repair independent of E104's behavioral promotion decision.
