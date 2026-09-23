# E052 — Cap Slippery Bridge HP rerolls

Issue #97. Hypothesis: allowing one reroll of a valuable removal offer but
excluding later escalating `SLIPPERY_BRIDGE` rerolls avoids the observed
large HP expenditure while preserving a beneficial first-reroll option.
The E051 floor14 native trace is the fixed retrospective input; its first
offer removed Flame Barrier at HP86, and Jev spent 3 HP to reroll to a Strike
offer at HP83. Existing `planned` candidate selection at `origin/main`
(`5879038`) is the baseline. The primary test is candidate eligibility, not
a counterfactual game win or HP outcome.

Predeclared evaluation: replay all ten E051 bridge `before` states from
segment3 trace SHA-256
`af5b26f4b86eb86ebfe322c274f65b681e1adca2046fb8abbb2deff7ef3146a3`
through the guard; test the first high-HP reroll as positive control, all
later offers as negatives, and verify the removal/exit choice remains legal.
Unit cases include unrelated events and a sole-reroll fallback. Record exact
code SHA, command, dependency/model/game versions, and output beside this
README. A native outcome requires a separate fresh run.

Decision rule: merge the guard if the first reroll remains offered, all nine
later escalating rerolls are excluded with exit available, and targeted plus
repository tests pass. Otherwise close without promotion. The cap is one
reroll regardless of HP or localized cost wording; this deliberately favors
health preservation in the absence of a reliable card-removal value model.
