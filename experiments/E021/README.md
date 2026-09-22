# E021 — Matched identical model decisions

Issue #37. Opt-in process-local full-input cache controls unrelated model variability in paired policies. Canonical model/state/candidates key; same fixed request template within one process, no persistent reuse across code/model changes. Exact original call source/metadata retained, cache cost zero, hit counts separate. Serializes inference to prevent concurrent duplicate calls. This evaluates a memoized policy, not independent model samples.

Meaningful tests: identical concurrent inputs invoke model once, modified treatment context misses, current candidate is returned and actual request counts/cost remain separate. Then corrected E020 paired planned/advised, five characters A10 seeds019..021, $5/20000calls. Evaluate decision attribution and errors as well as full-run wins/progression. No edits to game state.
