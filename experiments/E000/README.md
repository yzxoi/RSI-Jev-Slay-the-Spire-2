# E000 — Experiment protocol

Issue: #1. Hypothesis: atomic issues, immutable iteration commits, independent PRs and evidence comments make system changes auditable.

Baseline: architecture notes without an execution/evaluation protocol.

Iteration 1: add repository instructions, a scoped experiment Skill, PR template and atomic backlog. Reason: preserve failures and separate measured game outcomes from implementation claims before experiments begin.

Validation: private repository visibility checked through GitHub; initial tracked file list excludes `.env` and game binaries. Skill frontmatter validation and Git ignore checks are recorded in the PR result comment.

Decision: retain this workflow as infrastructure. No claim about gameplay improvement.
