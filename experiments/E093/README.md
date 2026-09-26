# E093 — Faithful CLI resource decisions

Issue: [#180](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/180).

Hypothesis: the pinned CLI already executes real potion commands, but missing capacity/usability fields, swallowed shop errors and automatic potion rewards prevent a faithful resource-enabled controller. An opt-in resource interface can expose normal use/discard/buy/claim/skip decisions without editing game values or changing legacy runs.

Baseline: main b3411ce, sts2-cli 084d1aa3d8e118ca7ce8d8774ad16d6be9c92367, game v0.111.0; legacy retaliate excludes potion use and buying. Compare an explicitly named resource-enabled retaliate variant using the native controller’s once-per-turn potion-versus-planned-action question. This is a compatibility/integration experiment, not a claim of stronger play or native parity for every mechanic.

Before evaluation, commit implementation and frozen inputs. Compatibility inputs: both E067 recorded shop prefixes; first recorded potion-bearing combat per character in baseline E089 seed e089_holdout_001 (exact accepted action prefixes); recorded post-combat reward transitions selected deterministically from E089; explicitly labeled synthetic controls for full capacity, automatic-use potion exclusion and selection-producing potion use if natural fixtures do not cover them. Preserve old-schema projection hashes when adding observational fields; do not silently relabel schema changes as mismatches or relax game-state comparison.

Complete-run smoke comparison: all five characters, A10, fresh seeds e093_resources_001 and e093_resources_002, baseline retaliate versus retaliate_resources (20 episodes), exact-request MatchedJev, four workers, 2000 actions/300 seconds per run, 3000 Jev calls/$0.75 total. No HP/reward/victory edits. Report every status, initial-state projected parity, potion/reward/shop transitions, progress, model and wall times, dependency SHA and raw trace hashes.

Merge rule for opt-in capability only: fixed legal use/discard/purchase/claim actions produce verified real inventory/effect/gold transitions; full capacity is respected; automatic-only potions are not offered manually; selection continuations complete; legacy fixture projections match; no new resource-caused execution error in the smoke cohort. Unexpected compatibility failures require committed iterations and retained failure evidence before re-evaluation. Normal defeats do not invalidate capability, and successful capability is not strength. Leave default policy unchanged. Publish results and decision in the PR.

## Iteration 1: dependency drift before gameplay

Implementation `1cade8a` passed 123 Python tests. The default `python3 scripts/setup_headless.py` read an updated Steam game DLL (`e7ceb806…`), not the frozen `9cb4f1ad…` input, and failed to build at an upstream Hook CardPlay/CardModel signature. No game evaluation ran. The isolated copy alone was affected; historical engine copies and native saves are intact. `build-01.json` preserves hashes and failure.

Continue against the original DLL kept in the main ignored dependency tree: create `artifacts/private/pinned-game/` from that lib directory, replace its `sts2.dll` with its `sts2.dll.original`, retain the historical localization tables, and run `STS2_GAME_DIR="$PWD/artifacts/private/pinned-game" python3 scripts/setup_headless.py`. This corrects dependency selection, not game behavior. Adapting the new Steam build is a separate issue.

## Fixed compatibility result

Pinned rebuild and `python3 -m scripts.probe_resources_e093 --output experiments/E093/probe-01.json` ran on clean SHA `45bec9b`. All 20 probe entries ended compatible: 18 natural legacy/resource replays plus two explicitly synthetic inventory controls. Every entry matched the historical full state after removal of only the declared new observation fields. All trace hashes verified. Natural five-character probes exercised Powdered Demise; this is not coverage of every potion. Both natural full shop inventories permitted a normal discard followed by a 50-gold Weak Potion purchase (270→220). Natural and synthetic reward controls verified full-slot blocking, preserved pending reward after discard, normal procurement and continuation. Gambler's Brew opened and completed card selection; Fairy was excluded from manual candidates. Synthetic controls never count as formal games.

`retaliate_resources` is opt-in. It shares the exact potion question/choice helper with native play, but whole-policy parity is not claimed: native guards, observation schemas and scene implementations still differ. CLI gold/relic rewards remain automatically collected; explicit potion rewards are the newly supported boundary.

Next preregistered command: `python3 -m scripts.evaluate_resources_e093 > artifacts/private/e093-smoke-01.log 2>&1`. Keep the pinned original game DLL and every failed outcome; no current-Steam or native-strength inference.
