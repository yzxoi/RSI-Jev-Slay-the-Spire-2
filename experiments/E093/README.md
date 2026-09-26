# E093 — Faithful CLI resource decisions

Issue: [#180](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/180).

Hypothesis: the pinned CLI already executes real potion commands, but missing capacity/usability fields, swallowed shop errors and automatic potion rewards prevent a faithful resource-enabled controller. An opt-in resource interface can expose normal use/discard/buy/claim/skip decisions without editing game values or changing legacy runs.

Baseline: main b3411ce, sts2-cli 084d1aa3d8e118ca7ce8d8774ad16d6be9c92367, game v0.111.0; legacy retaliate excludes potion use and buying. Compare an explicitly named resource-enabled retaliate variant using the native controller’s once-per-turn potion-versus-planned-action question. This is a compatibility/integration experiment, not a claim of stronger play or native parity for every mechanic.

Before evaluation, commit implementation and frozen inputs. Compatibility inputs: both E067 recorded shop prefixes; first recorded potion-bearing combat per character in baseline E089 seed e089_holdout_001 (exact accepted action prefixes); recorded post-combat reward transitions selected deterministically from E089; explicitly labeled synthetic controls for full capacity, automatic-use potion exclusion and selection-producing potion use if natural fixtures do not cover them. Preserve old-schema projection hashes when adding observational fields; do not silently relabel schema changes as mismatches or relax game-state comparison.

Complete-run smoke comparison: all five characters, A10, fresh seeds e093_resources_001 and e093_resources_002, baseline retaliate versus retaliate_resources (20 episodes), exact-request MatchedJev, four workers, 2000 actions/300 seconds per run, 3000 Jev calls/$0.75 total. No HP/reward/victory edits. Report every status, initial-state projected parity, potion/reward/shop transitions, progress, model and wall times, dependency SHA and raw trace hashes.

Merge rule for opt-in capability only: fixed legal use/discard/purchase/claim actions produce verified real inventory/effect/gold transitions; full capacity is respected; automatic-only potions are not offered manually; selection continuations complete; legacy fixture projections match; no new resource-caused execution error in the smoke cohort. Unexpected compatibility failures require committed iterations and retained failure evidence before re-evaluation. Normal defeats do not invalidate capability, and successful capability is not strength. Leave default policy unchanged. Publish results and decision in the PR.
