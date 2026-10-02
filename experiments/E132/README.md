# E132 — Reusable elite battle-entry saves

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/248

Status: completed. Five eligible saves passed fidelity and scoped speed gates; bank completeness failed (5/6). Research utility retained; no default strategy promotion.

## Question and hypothesis

Can real map-boundary saves provide reusable elite-battle starts across difficulty levels, avoiding replay from the beginning for every training/search rollout? E121 already showed faithful map saves (median 3.234 -> 1.117 s restoration) and E124 used them in search. E128 did not build snapshots for its new bank and unnecessarily retained full-prefix replay. This experiment reuses that infrastructure; it does not claim arbitrary mid-combat memory snapshots.

## Fixed inputs and budget

Ironclad, ascensions 0/5/10, seeds `e132_20261002_a` and `e132_20261002_b` at each ascension: six prespecified configs. Historical official v0.111.0 and unchanged pinned adapter/DLLs. The existing resource-aware E120 preparation policy legally advances toward the first elite; preserve every death, unavailable entry, error and cap, without replacing seeds or editing game values. A Boss entry is not substituted for an elite. Max 90 s / 700 actions per preparation, two workers, no live-game control or paid-model calls.

Freeze the complete entry bank before save/path evaluation. For each available Elite entry, A reconstructs the canonical prefix; B repeats it, saves at the actual preceding Map boundary, and enters; C loads that unedited save in a new process and enters. Require exact map and battle hashes and the save's original ascension. Each path 20 s.

Capture two reference trajectories per entry with full-prefix restoration: the unchanged control and an epsilon=0.15 legal-action rollout (RNG derived from case + fixed label), at most 30 s / 120 actions. Independently reconstruct each complete battle plan with the existing continuation verifier and extend through rewards to the next battle's second-turn opening or legitimate death (30 s / 80 extension actions). Freeze these complete action/hash paths before reuse. Incomplete source paths remain reported and do not become valid references.

Verify each frozen path with B (fresh prefix plus a save call) and C1/C2/C3 (three independent fresh-process loads of the same save). Check every before/after state, including generated selections, terminal outcome, rewards and next-turn draws. This covers divergent legal policies from the same start; neither trajectory is a new independent seed. Once all available-case fidelity checks pass, measure three paired fresh A/C restorations per available entry, alternating order by case-index + repeat. Do not exclude slow samples. No warm-process reset or engine changes in E132 (E129 stays separate).

## Decision rule

Bank completeness requires all six prespecified entries available; bank fidelity requires every A/B/C and all continuation/reward/draw comparisons exact, unchanged files and zero execution/cap/audit errors. Report preparation availability separately from conditional fidelity. A useful pilot speed result requires pooled paired median restoration speedup >=1.5 and C p95 no worse than A p95, with all comparisons retained. This is a new scoped research gate, not a relabeling of E121's stricter failed speed gates or a production default promotion.

Use a 10-minute batch work budget excluding implementation/analysis; stop launching new evaluation work if exhausted, retaining unstarted cases. Preserve local unedited save files, raw traces, public hashes, code SHAs, timing and all failures. No policy-training, search-strength, full-run win or hidden-state-universality claim. If valid, publish a reusable index for these exact entries/engine versions and a documented reset/rollout API; do not silently plug an uncertified snapshot into E128 or mutate ascension inside a save.

## Iteration 1 — natural bank freeze

Preparation used clean SHA `63c45db2002359e4b81cea9a5ef152e922471baa` with the pinned v0.111.0 engine. Five of six fixed configurations reached genuine Elite entries; `Ironclad-b-A0` instead reached a Boss under the fixed preparation policy and is excluded from elite validation, with its complete preparation retained. No seed replacement or state editing. The previous prose incorrectly equated all six `ready` statuses with Elite; this correction follows inspection of `room_type`. The machine-readable completeness gate already correctly failed. The freeze batch took 16.563 s; all six raw bundles passed the hash audit. Eight existing checkpoint/restore unit tests passed. The first unittest invocation used package-style names even though `tests` is not a package; it failed discovery before any gameplay, then discovery mode passed.

```sh
python3 -m unittest discover -s tests -p 'test_checkpoints.py'
python3 -m unittest discover -s tests -p 'test_research_restore.py'
python3 scripts/validate_elite_bank_e132.py freeze --output experiments/E132/fixtures-v1.json
```

The bank is frozen before capture; failures in the next stages remain evidence.

## Iteration 1 — frozen reference continuations

Capture SHA `001d7db4694cc3a0100f34df46edb1244187b4d7`. All five eligible entries matched full-prefix, save-call and loaded-map/entry paths, with original seed/ascension verified in the native files. All are Phrog Parasite, floor 9; this is not broad enemy coverage.

Ten reference paths are complete: four victories extended through rewards to the next combat second-turn opening; six legitimate deaths. Each entry has two distinct legal-policy trajectories. In case order A0-a/A5-a/A5-b/A10-a/A10-b, control remaining HP is 20/24/0/0/0 and epsilon15 HP is 24/19/0/0/0. This is a fidelity fixture, not a strength comparison or ten independent seeds. Capture took 92.472 s, cumulative batch time 109.035 s; all 41 preparation/capture bundles audited.

```sh
python3 scripts/validate_elite_bank_e132.py capture --output experiments/E132/references-v1.json
```

Before independent verification, corrected the exported index scope to count eligible entries rather than claim six cases. No game-policy, fixed inputs or gates changed. The completeness gate stays failed (5/6).

## Results and decision

Verification/timing SHA `b1b6601b27f5e42b64bd8d1143b7e3bbdd91fe9a`.

```sh
python3 scripts/validate_elite_bank_e132.py verify --output experiments/E132/verification-v1.json
```

| Metric | Result |
| --- | --- |
| Prespecified configurations | 6 (two seed strings × A0/A5/A10, Ironclad) |
| Eligible natural Elite entries | 5; A0-b reached Boss instead and is retained as unavailable |
| Preflight A/B/C map + combat-entry comparisons | 15/15 exact; native seed and ascension unchanged |
| Frozen full-prefix paths | 10: 4 victories through rewards/next-battle turn 2, 6 real deaths |
| Independent continuation checks | 40/40 exact (10 save-call B, 30 restored C) |
| Paired timing restores | 15 pairs / 30 paths, all exact |
| Full-prefix restore median / p95 | 4.507 / 5.061 s |
| Native-map restore median / p95 | 1.172 / 1.331 s |
| Median of paired speedup ratios | 3.787× |
| Native save-call median | 0.0884 s (five preflights; excludes reaching the map) |
| Raw evidence audit | 111 unique trace bundles, zero hash mismatches |
| Total gameplay batches | 218.956 s, below 600 s; zero execution errors/caps |
| Gates | fidelity PASS for available entries; pilot speed PASS; completeness FAIL |

The final report's `entries` list is the reusable local save index: five unchanged files, original seed/ascension, canonical-prefix/entry/map hashes and engine versions. Both distinct policy paths from each save were checked; repeated loads are not independent game seeds. The old E121 stricter performance failures remain unchanged. No full run or model training was evaluated, and these numbers do not show stronger search/PPO.

Decision: merge the optional bank validator, scoped reusable save index and all evidence, including the missing case. Do not claim a complete six-entry curriculum or change the default restoration/real-game policy. Existing evidence supports prioritizing a common battle-entry reset path before training expansion or E129 warm-worker work. E128 omitted building native snapshots for its new bank despite E121/E124 availability; that integration omission, not lack of save support, made its repeated full-prefix restores unnecessarily expensive.

All five entries are floor-9 Phrog Parasite, so this is insufficient enemy diversity. The control loses three of five battles; save fidelity does not make those starting states easy or demonstrate that all are winnable. Natural starts include different decks/relics/potions/HP; the A10-b entry has 8 HP. Keep preparation failures and curriculum coverage visible when constructing a larger bank.

## Why restoration still costs about one second

Post-hoc wire timing on the 15 matched pairs (descriptive component medians, not an additive accounting identity):

| Stage | Full-prefix A | Saved-map C |
| --- | --- | --- |
| Start process to ready | 0.054 s | 0.054 s |
| First command: start_run / load_save | 0.908 s | 1.023 s |
| Remaining actions through entry | 3.483 s | 0.095 s |

Saving removes the earlier floors' replay; fresh-process loading still initializes/deserializes the engine. Saving once is amortized across rollouts. E129 remains unexecuted: persistent-worker resets might amortize initialization, but need separate contamination/RNG/event-handler fidelity checks. Arbitrary mid-combat snapshots are not implemented: the current adapter's non-Map `SaveCheckpoint` path rewrites pre-room coordinates, not a faithful combat-state clone. Only call it at the true Map boundary. For an internal battle node, load that boundary and replay the battle-local action prefix with state-hash checks.

## Reuse and training interface

The existing low-level `rsi.research_restore.restore_entry(send, frozen, snapshot, manifest)` validates engine/file/history identity, sends `load_save`, checks the Map, enters via the original freshly legal action, and checks the battle hash. Existing `rsi.battle_search.probe(..., checkpoint=snapshot)` then runs a bounded fresh policy rollout with raw trace logging. These five entries stay explicit research opt-in; do not feed this report into the E121-specific `research_snapshots` evidence loader.

Example for this local, validated bank (not an additional evaluated run):

```python
from rsi.battle_search import probe
from rsi.checkpoints import file_hash
from scripts.validate_elite_bank_e132 import read_evidence
from scripts.evaluate_battle_search_e120 import manifest

version = {**manifest(), "experiment": "new_preregistered_experiment"}
proof = read_evidence("experiments/E132/verification-v1.json", version)
assert proof["fidelity_pass"] and proof["checkpoint_files_unchanged"]
sources = {}
for name, record in proof["sources"].items():
    assert file_hash(record["path"]) == record["sha256"]
    sources[name] = read_evidence(record["path"], version)
snapshot = next(e for e in proof["entries"] if e["case"] == "Ironclad-a-A5")
frozen = next(f for f in sources["fixtures"]["fixtures"] if f["case"] == snapshot["case"])
result = probe(frozen, version, "new_rollout", checkpoint=snapshot, seconds=30)
```

For training, create each difficulty through `start_run(ascension=...)`; never edit the ascension field of an existing save. Partition by base game seed **before** deriving multiple ascensions/paths, so correlated siblings stay in the same train/validation/test split. Within training, sample different legal policies/action sequences from each save. Identical actions plus identical RNG reproduce the same trajectory; repeated replay alone does not add independent experience. Expanding characters/enemies/decks/relics/potion inventories and adding new naturally generated seeds is separate from making resets fast.

Environment: Apple M3 Max, CPU, macOS 26.6.2 arm64, Python 3.13.5, .NET 9.0.318; original game v0.111.0. Full code/adapter/original and patched DLL hashes are in each report manifest. No engine changes, paid-model calls or live-game writes. Raw traces and native saves remain ignored under `artifacts/runs/`.

PR: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/249. Codex attachment was attempted but the app rejected it because this thread already exceeds 100 attachment identities; the PR remains available normally on GitHub.
