# RSI Jev — Slay the Spire 2

Public experiment workspace for a high-win-rate, multi-character STS2 controller using deterministic computation, Jev decisions, and selective Astra intervention.

The design is in [docs/design-discussion.md](docs/design-discussion.md). Experiments are tracked as atomic GitHub issues and separate pull requests. Each implementation iteration is committed, with commands, outcomes, limitations, and the merge/reject decision recorded in the experiment report and PR comments.

Milestone 2 reached: one genuine native Ironclad A0 full-run victory, including rewards, card selection, shops, events and all three bosses, with a verified normal game save. The run used substantial Astra assistance. Five-character A10 full-run experiments still have no demonstrated winning policy. See [results, costs and limitations](docs/milestone-02.md), [terminal evidence](experiments/E013/attempt5/terminal-save.json), and the earlier [milestone 1](docs/milestone-01.md).

Credentials stay in the ignored `.env`; proprietary game binaries and local dependency builds are not committed.

For a read-only live decision window, run `python3 -m rsi.monitor --game-run-id <native-run-id> --open`. It opens a small localhost Chrome window that follows the newest native trace segment for that game. `python3 -m rsi.monitor --replay-trace artifacts/runs/<segment>/decisions.jsonl --open` animates an existing trace without touching the game. Jev probabilities and confidence are displayed only when present in the model response; they are not win probabilities. The window has no game-action or model-request endpoint.
