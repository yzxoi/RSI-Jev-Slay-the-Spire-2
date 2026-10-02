# E133 — Checkpoint-backed multi-ascension PPO retraining

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/250

Status: natural bank frozen; reset certification before training.

## Objective and hypothesis

The user authorized retraining with more data after E132 proved reusable natural battle-entry saves. E133 tests a larger, harder multi-ascension training distribution at unchanged 73,794-parameter PPO capacity and four times E127's episodes per learner. This jointly changes data coverage and training duration; it is not E131's isolated matched-budget curriculum experiment, which remains unexecuted. No promise of full-run mastery.

## Fixed inputs and preparation

Historical official v0.111.0 and unchanged pinned adapter/DLL hashes. Ironclad only; 192 train / 24 validation / 48 test independent seeds named `e133_20261002_{train,val,test}_{000..N-1}`. Each seed is assigned ascension `(0,5,10)[index % 3]`, with no reuse across splits. Same E120 resource-aware preparation planner and macro policy. Naturally advance until the first Elite or Boss combat entry, or eighth combat entry, or real death, whichever comes first; 120 seconds / 1,200 actions per seed, eight engine workers. Preserve every selected seed, all intermediate entries, deaths, errors, caps and unavailable later rooms; no replacement or state/RNG editing.

Freeze the full preparation bank before continuation validation. Training uses the unique first, second and last available entries from each seed, cycling `(update-1+seed_index) % eligible_count`. Validation/test panels use second-available (early) and last-available (challenging), preserving duplicate panel identities and reporting them as correlated, not extra seeds. Count encounter/difficulty/resource coverage before training. A seed with no entry, an actual preparation error/cap, or fewer than eight distinct training encounter signatures stops this batch; real preparation deaths with earlier entries remain usable and reported.

## Native restore validation and fallback

Add explicit optional checkpoint reset to the existing PPO episode runner; full-prefix restoration remains the default. For each eligible train/validation entry whose immediate preceding state is a true Map boundary: A runs the unchanged planner from full prefix to battle terminal; B independently repeats the prefix, writes a native Map save, verifies the A action/transition path and extends through rewards to the next combat second-turn opening or real death; C1 independently loads the unchanged save and exactly replays B's extended path; C2 uses the actual PPO episode checkpoint reset to replay A's battle path. Require exact map/entry/all before-after/final hashes and unchanged save bytes/native seed/ascension. Each path <=30 seconds / existing 120 battle actions, extension <=80 actions. For natural event-combat entries with no immediate Map boundary, retain explicit full-prefix mode and require an independent full-prefix A replay; do not edit coordinates or silently drop them. Save/correctness failures stop training rather than substituting a faster path. Every native index is bound to bank/engine/evidence hashes.

Validate training/validation restoration first; defer held-out test-policy continuation results until all selected weight hashes are committed. Training/validation preparation and certification have a 30-minute phase budget: stop launching new jobs at expiry, preserve unstarted work. No game-engine patches or warm-worker reset in this experiment.

## Training budget and fixed selection

Two fresh learner initializations 1701/1702, S widths 128/64 (73,794 parameters), unchanged E127 encoder, terminal reward, optimizer/PPO hyperparameters. No search, reward shaping, imitation, network widening, future/seed inputs or external model API. Each learner: 32 updates × 192 terminal episodes = 6,144 episodes maximum; both learners total 12,288. CPU Torch single-thread, eight engine workers; <=3,600 collection/optimization seconds per learner. Each episode <=30 seconds /120 actions. Stop the affected learner on any incomplete training episode, skip the entire affected update and retain all traces; censored episodes never get an invented reward. No automatic additional budget.

Checkpoint every update; greedy fixed validation at updates 0/8/16/24/32 on BOTH early/challenging panels. Rank by challenging clears, challenging mean reward, early clears, early mean reward, earliest update; selection requires all panel outcomes terminal and no real execution error. Freeze two selections per learner: short-budget best among 0/8 (<=1,536 episodes), and long-budget best among 0/8/16/24/32 (<=6,144 episodes). Both may select the same checkpoint; do not force a late checkpoint or conceal regression. Record every failed checkpoint/validation/cap and raw learning curve.

## Held-out comparisons and exit rules

After selected hashes are committed, certify the test reset paths and evaluate all 48 preselected test seeds on both panels. Arms: planner, attack-priority, corresponding two frozen E127 S models, E133 short and E133 long models for each learner. Independently full-prefix replay every terminal E133 model trajectory, including losses; identical selected weights may reuse the exact already-evaluated record with explicit alias metadata (no invented extra samples).

Execution gate: bank/evidence/engine hashes intact, no illegal/reset/transition errors, no censored selected-model test outcome, all independent replays exact. Report all panel and difficulty cells, preparation reachability and duplicated entries; 48 is the independent test-seed count, not 96 panels or the number of learners.

Practical improvement gate for BOTH long learners: at least +3 challenging clears /48 over the corresponding E127 S; challenging paired HP-equivalent median >=+2 (legitimate defeat=0, censored unscored); preserve early A0 clears and early A0 median HP delta >=-2; match or exceed planner challenging clears. Separately, longer-training evidence requires BOTH long selections to gain at least +2 challenging clears and median HP >=+2 over their own short selections, without fewer early clears. No training-strength conclusion from loss alone. If gates fail, retain evidence and stop expansion; no silent seed/reward/network change or default real-game promotion.

## Deliverables and limits

Versioned issue/PR/commits, exact code SHAs and commands, compact machine-readable reports, native-save/trace/model hashes, loss/value/entropy/KL and train/validation reward curves, difficulty/panel held-out results and resource/throughput costs. Raw traces and weights local ignored; never proprietary binaries/secrets. Update research/decision records and private Notion. This learns combat from planner-prepared routes/decks/rewards, not end-to-end deck-building/full-run play. Initial model remains small so data and restoration are the focus; broad character training is separate.

## Preparation v1

Implementation/freeze SHA `e3ae398`; 14 synthetic PPO, split/selection and checkpoint-reset tests passed. Commands:

```sh
python3 -m unittest discover -s tests -p 'test_ppo*.py' -v
python3 scripts/retrain_ppo_e133.py freeze --output artifacts/runs/e133-fixtures-v1.json
```

All 264 selected seeds retained: 224 reached the planned boundary; 40 naturally died after providing earlier entries. No preparation errors/caps or seed replacements. Preparation took 133.287 seconds; 264 raw bundles hash-audited. The training subset has 575 unique first/second/last entries, including 423 Monster / 151 Elite / 1 Boss; 29 ordered exported enemy-list signatures, 423 deck hashes, 198 entries with potions; HP min/median/max 1/64/91. Ascension entry counts A0/A5/A10 = 192/191/192 (one seed has only two distinct positions). 574/575 training entries have an immediate true Map boundary, one retains explicit full-prefix mode. This is much broader than E127's 191 Monster + 1 Elite entries, but preparation survival and conditional battle skill remain distinct.

After freeze execution started, separate commit `735fa81` added plotting and corrected inherited episode trace scope metadata to E133; no game-policy or freeze changes. Native reset certification uses the next clean committed version. PR #251 attachment was attempted; Codex rejected it because this thread exceeds 100 attachment identities. GitHub PR remains available.
