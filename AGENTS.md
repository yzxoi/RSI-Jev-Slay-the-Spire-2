# Project instructions

Reason from the objective: high win rate across characters and high ascension, using internal game information, with decreasing Astra cost. Challenge unnecessary complexity using a simpler measurable baseline.

## Authorized workflow

The user authorized creating this private repository, opening atomic experiment issues, implementing experiments, publishing a separate PR per experiment, commenting results, and merging or closing according to evidence. Continue autonomously within that scope. Stop at the visible MCP milestone for user acceptance.

- Create an issue with hypothesis, baseline, fixed evaluation inputs and decision rule before testing an idea. Newly discovered distinct ideas get separate issues.
- One experiment branch and PR per issue. Commit each coherent implementation/fix iteration before running its evaluation; commit results afterward. Never amend away failed attempts or force-push experiment history.
- Record exact tested code SHA, commands, input configuration, dependency/game/model versions, measured outcomes, limitations and the reason for each iteration in `experiments/E###/README.md`. Keep compact machine-readable results beside it.
- Publish results in PR comments. State merge/close reasons before deciding. Merge commits preserve the iteration sequence. Negative findings remain accessible on the closed PR branch.
- Separate execution compatibility, battle outcomes, full-run wins and simulator correctness. Small samples are exploratory. Report all selected characters/seeds, including stalls and failures.
- Preserve raw local traces under ignored `artifacts/runs/`; publish sanitized compact results and trace hashes. Credentials and proprietary game binaries stay untracked. Do not source `.env` through a shell or print secrets.
- Formal win-rate evaluation does not edit HP, rewards or victory flags. Synthetic mechanic tests must identify themselves as such.
- A visible game has one writer. Do not retry an action after uncertain delivery until fresh state establishes what happened. Recompute hand/target indexes from fresh state. Stop at the configured boundary.

Use `.agents/skills/sts2-experiment/SKILL.md` for the project experiment workflow.
