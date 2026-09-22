# RSI Jev — Slay the Spire 2

Private experiment workspace for a high-win-rate, multi-character STS2 controller using deterministic computation, Jev decisions, and selective Astra intervention.

The design is in [docs/design-discussion.md](docs/design-discussion.md). Experiments are tracked as atomic GitHub issues and separate pull requests. Each implementation iteration is committed, with commands, outcomes, limitations, and the merge/reject decision recorded in the experiment report and PR comments.

Milestone 1 reached: reproducible five-character A10 opening-battle experiments and a real visible MCP combat, stopped at the reward screen for user acceptance. See [results and limitations](docs/milestone-01.md). This milestone does not claim high-ascension strength.

Credentials stay in the ignored `.env`; proprietary game binaries and local dependency builds are not committed.
