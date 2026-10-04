# E163 — encounter objectives selected by whole-battle engine rollouts

Issue #313. Hypothesis: a cheap objective prior can improve the E160 Obscura
failure mode; choosing among four such programs with bounded real-engine
continuations can avoid assuming the same objective suits every encounter.

## Preregistered protocol

Baseline is the frozen E160 battle planner with its actual source potion
reservations. Four programs, identical width 40 / depth 8 and potion schedule:
baseline; leader (1.8x damage value to leaders when explicitly marked Minions
exist, terminal bonus on all leader deaths); setup (+18 utility for each Power
played during rounds 1..5); both. These are heuristic priors, not predictions.
Cards/targets are recomputed at each fresh state; no stored winning action script.

Discovery: all 15 E160 treatment first-act Boss / act-two encounter roots,
including Obscura, frozen before execution by exact prefix/state/trace hashes.
Retain every failure. Evaluate all four programs at every root. Best fixed
program chosen on discovery by clears, then total ending HP, then total retained
potions, with fixed order above for ties. No coefficient tuning in this experiment.

Held-out: six natural new seeds `e163_holdout_Ironclad_A{0,5,10}_{000,001}`.
Existing E120 deterministic fixture collector uses official start_run and
unmodified rewards/deck/HP to reach its first Elite/Boss. Max 700 actions/90s
per collection. Unreachable roots remain failures, never replace seeds.

Search is exhaustive evaluation of this four-member policy family, not MCTS:
rank complete continuations by clear, then HP+4*remaining potions, then fewer
actions. Select the objective only; execute it again in an independent process
from the same entry and require exact final/transition hashes. Internal RNG
information is allowed. This is deterministic search, not uncertainty sampling.

Each probe <=120s including complete prefix restoration, <=300 battle actions,
15s/RPC; four workers; total <=1200s. Search inference budget <=60s summed
probe wall time per root (includes cold process/restoration). Report exceeded
budgets as failed gates. No new model calls. Baseline discovery must reproduce
all 15 recorded boundaries exactly. Independent exact replay of every probe.

Local continuation gate: all 15 discovery and 6 held-out roots execute/verify;
no lost baseline clear; mean paired ending-HP gain >0 on held-out; all search
budgets <=60s; zero hash/stderr failures. Static and searched arms reported
separately, with retained-potion counts. Small, biased encounter sample only.
Even if local gate passes, do NOT promote default strategy or claim full-run
strength until a separately registered natural whole-run experiment.

Commands after implementation commit:
```
python3 scripts/pilot_objectives_e163.py freeze --output experiments/E163/plan-v1.json
# commit plan before execute
python3 scripts/pilot_objectives_e163.py evaluate --output experiments/E163/evaluation-v1.json
```

## Result

Tested SHA `3915c95e6240f3e523d12baa3f4662d2d90f0e36`; historical
v0.111.0 / SDK 9.0.318 / Python 3.13.5, exact dependency/assembly hashes in
evaluation-v1.json. Wall time 314.340 seconds. No external model API calls;
this excludes the present task's unmetered expert analysis/engineering cost.

All 15 discovery baselines exactly reproduced recorded battle boundaries.
76 full battle probes (60 discovery + 16 held-out), 76 independent command/state
replays, 19 independent executions of the selected objective, and 6 natural
fixture collections: 177 raw bundles audited, zero hash/stderr failures.
Search uses the same deterministic future as execution, with baseline included;
its discovery non-regression is partly by construction, not generalization.

| Known root | Baseline HP | Leader | Setup | Both | Search selects |
|---|---:|---:|---:|---:|---|
| A0-000 Kin Priest | 51 | 21 | 43 | 23 | Baseline |
| A0-000 Mytes | 65 | 65 | 74 | 74 | Setup |
| A5-000 Hunter Killer | 56 | 56 | 74 | 74 | Setup |
| A5-000 Obscura | 16 | 66 | 20 | 66 | Leader |
| A5-001 Vantom | 28 | 28 | 36 | 36 | Setup |

The other ten discovery roots have unchanged ending HP. Search gains 85 total
HP / 15 encounters (mean +5.667) across three of four source seeds, no lost
clears. Obscura falls from 15 to 5 turns and retains Dexterity Potion. Setup
alone plays Juggernaut on turn 5, ends at 20 HP/13 turns and consumes the potion;
the better leader policy does not play Juggernaut. Target choice dominates the
observed failure; the original missing-power diagnosis was incomplete.
The discovery-selected fixed program is leader_setup (mean +3.8 HP), but it
loses 28 HP against Kin Priest. No global always-focus-leader rule is justified.

| New seed | Entry outcome | Baseline / searched encounter outcome |
|---|---|---|
| A0-000 | Defeat before entry | No root; retained failure |
| A0-001 | Bygone Effigy, 69 HP | Both clear at 20 HP |
| A5-000 | Bygone Effigy, 77 HP | Both clear at 37 HP |
| A5-001 | Phrog Parasite, 1 HP | Both defeat |
| A10-000 | Defeat before entry | No root; retained failure |
| A10-001 | Byrdonis, 29 HP | Both defeat |

Four roots available out of six preselected seeds; baseline/fixed/search all
clear 2/4 available fights, or reach-and-clear 2/6 selected fixture attempts.
Neither denominator is full-run win rate. Mean held-out HP gain = 0. Three
of four roots have exactly identical action/state transitions across all four
programs; A5-001 has two distinct sequences but both lose. Two Bygone Effigy
decks have no Power cards. The narrow policy family cannot invent a useful
alternative in these cases. Poor entry preparation is also evident; 1 HP at
an elite does not prove the fight mathematically unwinnable.

Search cost including four cold-prefix restorations: median 29.733 seconds,
maximum 41.310, all below the registered 60-second cap. At these held-out roots
that cost buys no improvement. HP reward plus four per potion is a declared
local proxy, not a calibrated full-run value function.

## Decision and limitations

**Local gate failed**: two unreachable roots and zero held-out gain. Fidelity
passed. Close PR #316 without merging the objective heuristics; preserve this
branch, every probe/result and the preregistration. No default changes, full-run
evaluation, network training, native run, or final acceptance seed use.

The unseen collector intentionally uses the older fixed macro policy, not
Astra's campaign policy. Its early elites and poorer decks differ from E160
act-two/Boss discovery. This stress test rejects broad promotion of this narrow
family, not the Astra-macro architecture. Do not patch coefficients against
these six seeds or turn their repeated replays into new independent samples.

Next: complete macro transactions (#312), collect fresh natural Astra-built
campaign roots, then separately evaluate a broader action/turn search versus
this objective-family baseline with explicit trigger coverage and latency.
Use independent per-run expert budgets for eventual full-run tests. First
reduce decisions that merely repeat an already specified transaction; do not
extend E160's interrupted paths and call them new complete runs.
