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

Evaluation at tested SHA `cbf8e3da169aec2e36fa364e7e7b9159a9aa4815`:

```sh
python3 -m experiments.E052.replay --trace /Users/yzxoi/RSI-Jev-Slay-the-Spire-2/artifacts/runs/1685f06b-8f18-4be7-8c96-cc68da465af6/decisions.jsonl --output experiments/E052/replay-result.json
python3 -m unittest discover -s tests
```

The fixed trace hash matched. The first HP86 `HOLD_ON_0` reroll remained
available, all nine later escalating rerolls were excluded, and the native
`OVERCOME` exit remained available in all ten states. The five guard unit
cases and the full 70-test repository suite passed. The baseline had offered
all ten rerolls; Jev actually selected nine of them, costing 63 HP. Exact
per-state output is `replay-result.json`. No Jev calls or native actions were
made in this offline evaluation; model `typesafe/jev-1.13-20260917`, native
game v0.111.0 and mod v0.15.0 identify the source trace, not a new run.

The predeclared candidate decision rule passed, so merge this small guard
for the next native run. This does not establish that E051 would have won:
accepting a different card removal changes the subsequent game and must be
measured as a separate fresh-run experiment.
