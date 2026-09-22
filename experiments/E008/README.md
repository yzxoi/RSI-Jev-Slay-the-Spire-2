# E008 — Visible native-MCP combat milestone

Issue #9. Hypothesis: the merged raw Jev controller can operate the real visible game through MCP tools, record each transition and stop before choosing post-combat rewards.

Selected existing run: `9JKXVG5BK1D8`, Ironclad, ascension 0, floor 3, first turn against Nibbit (46 HP), player 80/80. This user-owned live state is a transport demonstration, not part of the A10 strength evaluation. No game values are edited.

Baseline: prior read-only initialization. Maximum 80 actions / 240 seconds / 100 Jev calls / $0.15. One local writer lock, built-in autoplay must remain off, and state/action indices are checked again after inference. Uncertain action delivery stops the controller instead of replaying the action. Unsupported overlays or lethal end-turn choices stop for expert attention.

Iteration 1: add direct JSON-RPC MCP transport, live candidate adapter, readiness/identity guards and a reward-boundary stop. Reuse the merged Jev chooser; E003's rejected computed-context experiment is not promoted here.

Decision rule: merge on a verified real combat-to-reward transition, complete trace audit and no repeated/stale action. Then stop for user acceptance. Full-run automation and high-ascension strength remain future milestones.

```sh
python3 -m unittest discover -s tests -v
python3 -m rsi.live --expected-run-id 9JKXVG5BK1D8 --output experiments/E008/preflight-v1.json
python3 -m rsi.live --expected-run-id 9JKXVG5BK1D8 --execute --output experiments/E008/results-v1.json
```

## Iteration 1 result — stopped on an explicit rejection

Implementation `4abc9ef`. Five unit tests passed. Read-only preflight had seven supported candidates, zero actions and zero model calls. The visible run accepted 12 actions and then returned `invalid_action` (409) on the next card: `available_actions` had become passive-only between the fresh observation and execution. The controller stopped without resending; one earlier stale proposal had also been discarded. Jev made 14 requests, costing $0.002225664; elapsed 46.644 seconds. Current player HP is 68; the battle is unfinished. Full preflight and failed traces are preserved as compressed JSONL with hashes in the result manifests.

This fails the milestone acceptance rule. Next iteration must handle transient readiness and explicit pre-execution rejections while continuing to stop on uncertain delivery. The existing run is resumed, not reset or represented as an independent battle.

## Iteration 2 — discard explicitly rejected proposals and re-observe

The native server source returns this exact `invalid_action` 409 before calling `ActAsync` (`STS2AIAgent/Server/NativeMcpServer.Tools.cs`). A fresh-state check cannot prevent every observation/execution race. Classify only that explicit pre-execution rejection as recoverable; discard the choice, wait for readiness, read new state and ask Jev again, with a six-rejection ceiling. Transport failures, pending execution and all other errors remain non-retryable. Also require readiness explicitly when validating a proposal, since readiness is intentionally excluded from the stable state hash. Two focused regression tests exercise rejection classification and a readiness-only change.

Resume the same run from its observed 68 HP / turn 5 state; write `results-v2.json`. This is a continuation of iteration 1 and must be reported together. The milestone still requires a reward boundary and full audit; an explicit rejection is acceptable only if recorded, known not executed, and followed by a fresh decision.

## Iteration 2 result — visible milestone reached

Tested implementation: `ccbe3db` (tracked working tree clean). Command:

```sh
python3 -m rsi.live --expected-run-id 9JKXVG5BK1D8 --execute --output experiments/E008/results-v2.json
```

The continuation accepted two actions (Bash, Strike), defeated Nibbit and reached `REWARD`. The controller exited before claiming gold, choosing a card, or leaving the room. Native decision history independently contains exactly 14 accepted decisions from `native_mcp` for this run, matching the 12 + 2 local trace action results. A native-window screenshot visibly confirmed the reward screen with 74/80 HP. Built-in autoplay is off.

Across both execution segments: 14 accepted actions, 16 Jev requests, 61,105 input tokens, $0.002566410 reported model cost, and 53.671 seconds of controller runtime (excludes the debugging pause). Initial HP was 80, pre-victory HP 68, and post-combat HP 74; net loss is 6 after the normal heal. The exact returned model is `typesafe/jev-1.13-20260917`. No Astra call occurred inside the decision loop; Astra handled infrastructure and failure diagnosis outside it. This does not measure total development/review Astra tokens.

Audit: JSONL sequence numbers and SHA-256 hashes verified; exact requests/responses, candidate sets, stale proposal, rejected request and observed transitions retained; no action issued after the reward boundary; no credentials in committed traces. `audit-v2.json` and `native-corroboration-v2.json` contain the compact evidence. Seven unit tests passed.

Decision: merge the integration milestone after preserving both iterations. The first run's rejection is not hidden. The new recovery path is covered by focused tests but did not fire during the two-action live continuation, so repeated-transition reliability remains unproven. This A0 battle establishes visible MCP integration only; it is neither a full-run win nor evidence of high-ascension strength. Stop here for user acceptance.
