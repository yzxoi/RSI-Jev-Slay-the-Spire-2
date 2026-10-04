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

## Evaluation v1 — rejected, no promotion

Implementation `9deb38e`; frozen tested code
`3ac6417a206937ea5a6dc9cc4e970f09522a2277`. Each of the85 accepted fresh
teacher replies, plus one explicit abstention, was committed before consumption.
All `rsi/` sources remained frozen during evaluation. Four original attempts and
four independent full-prefix/terminal replays have matching states/hashes; eight
raw bundles pass hash/stderr checks. Historical gamev0.111.0, .NET9.0.318,
Python3.13.5, macOS arm64; exact dependency and DLL hashes are in
[evaluation-v1.json](evaluation-v1.json). No game edits, rollback-selected wins,
Jev/API calls, new weights, native gameplay, or final330seed use.

| New seed | Fixed macro + fixed battle | Astra macro + same fixed battle |
|---|---|---|
| A0-000 | Defeat, act1 floor7 normal fight;5 fights cleared | Defeat, act2 floor16 Knowledge Demon;13 fights cleared |
| A5-000 | Defeat, act1 floor17 Vantom;9 fights cleared | **Interrupted**, act2 floor11 Elite opening,47HP;12 fights cleared |

Both treatment trajectories cleared act1; neither produced a full-run victory.
A5 is not a battle defeat or a completed sample. Progress tuples in the original
machine result are descriptive prefixes, and its A5 `sign=1` is not a valid
completed-run treatment effect. The simple baseline is not the strongest possible
campaign policy. Two exploratory seeds do not establish win-rate improvement.

### Ownership failure caught before an action

A5 acquired Gambling Chip. At the start of the next battle, its discard selection
arrived **before** `combat_play`; `Ownership.observe` only activates upon
`combat_play`, so the controller incorrectly asked the campaign teacher to choose
battle cards (request38). The expert refused tactical intervention. A deliberately
invalid committed choice caused existing validation to stop before any selection
command, producing `ValueError: Expected subset choice`. This is an intentional
fail-closed response to a genuine routing defect, not an ordinary model-format
error. [Abstention record](ownership-abstention-v1.json). No resumption or seed
replacement was performed.

The runtime teacher audit says `passed:true` because it trusts its own
`combat_active` classification. That is **not independent ownership evidence**;
[manual semantic audit](diagnosis-v1.json) correctly reports failure. Future audits
must verify battle lifecycle separately, including pre-turn selections.

### Real cost reduction is smaller than the offline bound

86 actual requests:85 accepted decisions plus one rejected battle request.
12 transaction actions and48 mechanical actions occurred; only20 replaced
nontrivial one-action requests (10 transaction,10 mechanical). Accepted decisions
therefore represent105→85 same-trajectory request equivalents, **19.05%**, not
E164's historical31% and not a randomized two-protocol comparison. Most mechanical
actions were already single-legal-choice operations and are not credited as savings.

Accepted packets serialized1,098,979 input /59,103 output characters; including the
rejected request gives1,112,554 input characters. These are not tokens or API cost.
Actual task Astra tokens/USD, engineering overhead and diagnostic reads are unknown.
The manifest's model_calls0/model_cost0 describe external API only. Total measured
wall1400.165s, cumulativeCPU37.306s. Natural gameplay compute seconds by arm:
A0 control6.287/treatment16.201, A5 control7.787/treatment11.209; expert waiting
accounts for most latency. All registered budgets passed; neither packet limit was
reached. Request batching alone does not establish cheap autonomous play.

### Concrete battle defects, not a generic prompt problem

[Read-only diagnosis](diagnosis-v1.json) records exact selected cards, potion timing,
turn states and source hashes. A0 entered Knowledge Demon at72HP after Blood Vial.
On turn1 the Boss had a debuff intent and no attack; the fixed early-potion policy
consumed all seven potions, including Block Potion. Ashwater then exhausted seven
cards: Hellraiser+, Strike, Pillage, two Defends, Vicious and Iron Wave. Vicious had
just been generated by Power Potion. Hellraiser+ was in the opening hand but was
never installed in this fight. Defeat came on turn11 with the Boss still at44HP.

The code-level cause is specific: `rsi.teacher.selection_choice` decides whether a
selection is destructive from optional menu text and a four-name card whitelist.
The CLI menu does not contain that text, and Ashwater is not in the whitelist;
the selector consequently **maximizes the value of cards to exhaust**. Its parent
record does contain `Exhaust any number of cards in your Hand`, but the selector
ignores that field. Likewise, potion reservations currently express only release
boundaries, so releasing seven bottles on a Boss hands them to an indiscriminate
`early` executor. Astra contributed by retaining risky Ashwater/Snecko and by
constructing an engine without verifying safe potion/selection execution.

Power use is more nuanced than "never plays Powers": A0 had8 affordable Hellraiser
turns and played it twice, on act2 floors13/14 turn3, after its upgrade. A5 had4
affordable Crimson Mantle turns and played it once, floor6 turn2. The teacher
consulted only treatment traces for these questions and prior E013/E030 notes for
an unresolved relic description; controls remained blinded until both treatments
ended. Context was shared across the two cases.

No causal claim is made that saving Hellraiser, skipping Ashwater, changing rest,
or different potion timing would win this Boss: these need separately registered
same-state counterfactuals. Other unresolved event descriptions and deck removals
by Thieving Hopper are recorded, not silently interpreted as static deck state.

Decision: **close PR319 without merging**. Complete-run and semantic ownership
gates failed; preserve branch, implementation, all replies, raw hashes and negative
results. E164 remains optional infrastructure. Next isolate (1) battle-opening
ownership, (2) destructive-selection semantics, and (3) potion usefulness at release.
Do not spend another large Astra-guided full-run sample before those checks.
