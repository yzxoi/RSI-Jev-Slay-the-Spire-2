# E165 — fresh Astra macro transactions with unchanged battle execution

Issue #318. Hypothesis and baseline, frozen before execution: Astra's actual
fresh transaction planning is usable for natural full runs while E159's battle
program stays fixed. E164 showed historical 200→138 packet compression, but its
conservative input characters fell only3.6%; request reduction is not token or
win-rate evidence. New treatment uses cached deck/map context as before.

Two NEW Ironclad seeds: `e165_hybrid_Ironclad_A0_000` and
`e165_hybrid_Ironclad_A5_000`. Both program_campaign and astra_campaign, four
natural attempts. The control is E160's deliberately simple cautious macro
policy. Both use identical FrozenProgram combat, with treatment's typed potion
reservation masks. No E163 objectives, Jev, neural training, new battle search,
native game, HP/reward edit, seed replacement, or E160 continuation.

Expert sees only treatment histories until all expert decisions end. The two
cases share task context and may adapt across cases, not independent cold starts.
Every reply commits before execution; exact request/response/state/action and
source SHA are traced. Legal subset selections, verified acquisition reservations,
<=5 transaction followups, and mechanical open-slot potion claim / healthy sole
route are opt-in. Random generated choices and changed inventory/offers requery.

Independent120-packet budget per treatment (no shared packet race),2400 actions
and120 compute seconds/run excluding expert waits;600s/reply;3600s global wall,
1200 cumulative CPU;four workers. No budget extension. Record actual packets,
transaction/automatic actions, same-trajectory one-action equivalent counts,
serialized input/output, waits/CPU/wall, and unknown actual Astra tokens/USD.

Continuation gate: all4 natural terminals and4 exact independent replays;
no illegal/ownership/resource/stderr/hash failure, all budgets; at least one
positive progress pair and no negative pair using (victory,acts,cleared fights).
This small exploratory gate authorizes further separately registered study only;
no default promotion or stable win-rate claim. Keep all errors/caps and failures.
Final330network acceptance seeds untouched. Baseline outcomes stay blinded until
all treatment decisions end.

```
python3 -m unittest discover -s tests -p test_campaign_teacher.py
python3 -m unittest discover -s tests -p test_campaign_transactions.py
python3 scripts/pilot_transactions_e165.py plan --output experiments/E165/plan-v1.json
# commit the plan before running
python3 scripts/pilot_transactions_e165.py evaluate --plan experiments/E165/plan-v1.json --output artifacts/runs/e165-evaluation-v1.json
python3 scripts/reply_transactions_e165.py /tmp/e165-answers.json
# commit each generated response before the controller consumes it
```
