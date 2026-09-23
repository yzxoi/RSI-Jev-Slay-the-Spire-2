# RSI Jev — Slay the Spire 2

Public experiment workspace for a high-win-rate, multi-character STS2 controller using deterministic computation, Jev decisions, and selective Astra intervention.

The design is in [docs/design-discussion.md](docs/design-discussion.md). Experiments are tracked as atomic GitHub issues and separate pull requests. Each implementation iteration is committed, with commands, outcomes, limitations, and the merge/reject decision recorded in the experiment report and PR comments.

Milestone 2 reached: one genuine native Ironclad A0 full-run victory, including rewards, card selection, shops, events and all three bosses, with a verified normal game save. The run used substantial Astra assistance. Five-character A10 full-run experiments still have no demonstrated winning policy. See [results, costs and limitations](docs/milestone-02.md), [terminal evidence](experiments/E013/attempt5/terminal-save.json), and the earlier [milestone 1](docs/milestone-01.md).

Credentials stay in the ignored `.env`; proprietary game binaries and local dependency builds are not committed.

For a read-only translucent overlay on macOS, run `python3 -m rsi.overlay --game-run-id <native-run-id>`. It follows the newest native trace segment, floats in the upper-right of the active display, and lets clicks pass through to the game. Adjust with `--opacity 0.7`, `--screen 1`, or `--margin 30` if needed. `python3 -m rsi.overlay --replay-trace artifacts/runs/<segment>/decisions.jsonl` animates an existing trace without touching the game. For interactive history and replay in a browser window, use `python3 -m rsi.monitor --game-run-id <native-run-id> --open`. Jev probabilities and confidence are shown only when present in its model response; they are not win probabilities. Both displays are read-only and have no game-action or model-request endpoint.
