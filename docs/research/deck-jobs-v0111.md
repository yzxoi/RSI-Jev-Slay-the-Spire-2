# Deck jobs: STS2 strategy research for the Astra/Jev controller

Accessed 2026-09-24. Local game in E081: beta v0.111.0. This is a decision framework and experiment input, not a proven stronger policy. Its source articles were written from March 2026 onward; specific card text and enemy behavior must be re-read from the current game state before execution. The v0.111.0 beta patch alone changed 18 cards and two relics ([patch index](https://sts2.untapped.gg/en/patch-notes/v0.111.0)).

## What to evaluate at a reward

The strongest reusable idea is to ask which **job** the next threatening fight needs, then compare each offer with what the deck and held potions already supply. Jorbs describes five jobs: immediate single-target damage, immediate multi-enemy damage, immediate mitigation, long-fight scaling, and draw/deck manipulation. An AoE card is not inherently required if rapid single-target kills solve the same fight ([Jorbs](https://sts2.untapped.gg/en/articles/slay-the-spire-deckbuilding-strategy-solving-the-spire-with-jobs)). Baalorlord distinguishes immediate output from scaling, and uses deck cycle time and mitigation-card density to reason about how often answers appear ([Baalorlord](https://sts2.untapped.gg/en/articles/core-deckbuilding-concepts-in-slay-the-spire)).

For a cheap controller, record this small ledger before asking Jev to choose a reward or map node:

| Field | Question for the current run | Observable input |
| --- | --- | --- |
| Next threat | Which known Boss, elite route, or likely multi-enemy encounter must be beaten soon? | Boss ID, map, known encounter pool, HP |
| Frontload | Can the first two turns remove a dangerous target or threaten enough damage without setup? | Deck/relics, current energy, attack costs, potions |
| Mitigation | Can a bad incoming turn be survived while still progressing the fight? | Block, Weak/other prevention, HP, potions |
| Scaling | Can output or defense grow fast enough for the known Boss/long fight? | Powers, repeatable effects, debuffs, setup turns |
| Access | How soon and how reliably is each answer drawn and paid for? | Deck size, draw, exhaust/powers, energy, extra resources |

This ledger is a **proposal for measurement**, not a validated score. For each candidate, compare `take card` with `skip`, identify the specific weakness it fixes, and account for energy/resource demand, setup time, upgrade dependence, and opportunity cost of a slower cycle. Skipping a mediocre addition can improve access to stronger cards, but there is no universal target deck size ([Untapped deckbuilding guide](https://sts2.untapped.gg/en/guides/how-to-build-a-strong-deck)). A card that draws one as it is played may replace its own draw without accelerating the deck relative to skipping it; powers and exhaust cards change later cycles differently from the first ([Baalorlord](https://sts2.untapped.gg/en/articles/core-deckbuilding-concepts-in-slay-the-spire)).

Do not encode Jorbs's illustrative “two or three” early attacks, Baalorlord's illustrative 33% mitigation density, or a fixed elite count as hard thresholds. These depend on draw, relics, encounter mix, potions, and character. External tier lists and observed card win rates are useful leads, but selection effects and patch mismatch prevent reading them as causal card values.

## Five character-specific constraints

Each row is a question to check; none requires committing to one named archetype.

| Character | Early / long-fight check | Source |
| --- | --- | --- |
| Ironclad | Check whether starting Strikes/Bash plus new cards can end early fights quickly enough; Burning Blood makes some HP exchange tolerable, but a defensive pick still needs a near-term use. Later, assess scaling and exhaust/upgrade interactions against the Boss. | [Ironclad overview](https://sts2.untapped.gg/en/characters/ironclad) |
| Silent | The starter is relatively defensive, so verify an early damage source. Shiv, Poison, and Sly/discard can coexist; Poison's delayed output may leave a frontload gap, while discard payoffs need enablers and draw. | [Silent overview](https://sts2.untapped.gg/en/characters/silent) |
| Defect | Count actual orb generation and evocations before valuing more slots or Focus. Frost can provide continuing mitigation and Lightning damage; a slot expansion without enough channeling delays its return. | [Defect overview](https://sts2.untapped.gg/en/characters/defect) |
| Necrobinder | Evaluate Osty as both damage and interception. Doom can finish long fights but its timing matters: if it resolves after an enemy turn, survival until then is part of its cost. Soul generation affects access to the deck. | [Necrobinder overview](https://sts2.untapped.gg/en/characters/necrobinder) |
| Regent | Budget persistent Stars as a second resource: count generation against the Star costs of intended plays across cycles. Forge can add scaling when its cards already do useful immediate work. | [Regent overview](https://sts2.untapped.gg/en/characters/regent) |

## Route, rest, and combat implications

Look at the known Boss and remaining branches, then judge an elite by current capabilities, HP, potion inventory and reachable rest/shop nodes. Early ordinary fights can supply the cards needed for an elite; a flexible route preserves the ability to divert when those cards do not appear ([map guide](https://sts2.untapped.gg/en/guides/how-to-make-the-best-map-choices-in-slay-the-spire-2)). A campfire upgrade has value only if the resulting run survives; rest is appropriate when HP is the binding resource. This is a decision criterion, not a fixed HP threshold.

For combat, compare plans over the next turns rather than maximizing this turn's block or damage in isolation. Removing an attacker changes future incoming damage; a potion trades a finite resource for HP and/or a shorter fight. Estimate those effects with the game's current mechanics, including multi-hit and status interactions ([combat guide](https://sts2.untapped.gg/en/guides/micro-combat-strategy-in-slay-the-spire-2)).

## Local diagnostic: E081 floor 2–9 rewards

The [E081 checkpoint on PR #155](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/blob/701ad9a67a57a3cc46fed7a70e9f654bf93e7f67/experiments/E081/checkpoint.json) records a **natural Ironclad A1** run `8X3876DS2JL4`, game v0.111.0. Its segment-01 raw trace SHA-256 is `e0fd99e72429c47b2abf1933cc1ef5e11df8fd2436b80ee16fdf6aff89ecd420`. The five observed card rewards were:

| Floor | Offers (IDs) | Selected |
| --- | --- | --- |
| 2 | HEMOKINESIS, ARMAMENTS, WHIRLWIND | ARMAMENTS |
| 3 | HOWL_FROM_BEYOND, COLOSSUS, FORGOTTEN_RITUAL | COLOSSUS |
| 5 | ARMAMENTS, TRUE_GRIT, INFERNAL_BLADE | ARMAMENTS |
| 8 | POMMEL_STRIKE, MOLTEN_FIST, JUGGLING | POMMEL_STRIKE |
| 9 | MOLTEN_FIST, COLOSSUS, TREMBLE | COLOSSUS |

Four picks were mitigation/utility, one was a direct attack with draw. At floor 11, the run was paused at 20/87 HP amid a multi-enemy fight; it has no confirmed terminal outcome. The trace raises the question of whether early damage and multi-enemy coverage were sufficient. It does **not** establish that any single reward was wrong: route, potions, relics and later play confound the outcome. A counterfactual must replay a frozen pre-reward state, verify entry parity, then follow both branches through battle or full run.

## Proposed policy and falsification path

1. Add a deterministic feature extractor for the ledger, with `unknown` where game data cannot support a metric. Preserve exact card IDs/text, deck, Boss/map, HP, relics and potions in the trace. This is preferable to making Jev count cards or compute probabilities from long text.
2. Give Jev a concise floor-level threat summary and ask for typed candidate rankings with brief job labels and confidence. A future record could contain `threat_id`, `missing_job`, `candidate_id`, `why_now`, `resource_cost`, `confidence` and `needs_astra`. Let Astra intervene for state-bound, high-impact ambiguity, such as imminent elite/Boss readiness or a dangerous reward choice. Keep the baseline prompt as a control.
3. First run an **offline diagnostic** on frozen E081 rewards and other held-out traces: measure changed choices, feature availability and model cost. Decision disagreement alone is not improvement.
4. Then preregister matched CLI A10 seeds and characters before implementing the treatment: same starting seeds, game/dependency versions, combat policy and budgets; vary only the reward/route rubric. Report every run, including stalls, Boss entries, Boss clears, complete-run wins, HP and cost. Replays from an exact frozen reward state can isolate specific choices. Small cohorts remain exploratory.

The next policy experiment needs its own issue, branch, implementation SHA, compact outcomes and PR decision. Nothing in this memo changes the current controller or the paused live game.
