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
