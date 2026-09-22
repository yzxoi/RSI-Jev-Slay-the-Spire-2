---
name: sts2-experiment
description: Run and evaluate versioned Astra/Jev/STS2 experiments in this repository, linking atomic issues, iteration commits, PR evidence, and promotion decisions.
---

# STS2 experiment workflow

Read the repository AGENTS.md and the relevant issue. The user has authorized experiment issues, repository PRs, result comments, and evidence-based merging/closing; milestone 1 has been accepted and the current objective includes full-run high-ascension evaluation and one genuine visible complete victory.

Before execution, record the hypothesis, strongest practical simple baseline, fixed seeds/characters/ascension, budget and decision rule in `experiments/E###/README.md`. Commit the runnable implementation, then record its SHA in the run manifest. Changes to hypotheses or sample sets are new iterations, not silent replacements.

Keep game execution in the controller, not in a token-consuming conversation loop. Jev returns typed choices, scores or probabilities, not hidden reasoning. Preserve its exact input/output, candidate set, computed assumptions, observed transition and usage. Astra reviews compact evidence and requests raw records only when needed.

After each evaluation, commit the compact results and why the next change is justified. Comment on the PR with the tested SHA, reproduction command, outcomes, limits and merge/close decision. Preserve failed iteration commits. An offline re-ranking score is not a counterfactual battle result; compatibility is not playing strength.

Use the local, ignored dependency checkout and SDK. Copy/patch only local game DLL copies. Do not add game binaries or credentials to Git. Read project `.env` in process and never log authorization headers.

For visible runs, confirm the selected live run and a single writer, execute MCP actions one at a time, and respect explicit run/budget boundaries. The current authorization covers rewards, cards, routes, shops, events and combat. Preserve losses and restarts; never edit game values or pass a rollback-selected branch off as a single-run win.
