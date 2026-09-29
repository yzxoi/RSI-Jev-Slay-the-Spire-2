# E114 — sts2core source and trace compatibility audit

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/218

Status: preregistered, 2026-09-29. This is an offline audit, not a policy promotion or win-rate experiment.

## Question and fixed scope

Can sts2core supply a useful combat kernel for our recorded states? Distinguish potion mechanics, legal actions, local valuation, rollout policy and cross-room inventory. The practical baseline is our approximate planner plus preserved real-engine observations.

Upstream: `lain-wood/sts2core` at `3b2d969d025b9e64bc96b9a15928bd2a0d824bf2`, targeting game v0.107.1. Metadata: our `b7de162` commit. Inputs are all 30 E113 frozen combat entries (six seeds, five characters, A10, CLI v0.111.0), all 71 E092 native continuation segments, all four E102 historical Boss continuations, and E110 segment 1 for co-op scope. Missing/unsupported inputs remain reported. E102 repeats two entries and E092 is one continuation: these are not independent full-run samples.

Before evaluation, commit the audit code. Verify raw trace hashes, count identity coverage with the upstream's actual lookup functions, and inspect information lost at the state boundary. Identity coverage is only an upper bound on compatibility. No copied game binaries, live writes or paid model calls. Synthetic potion probes and upstream unit tests are separate from actual game evidence.

Decision rule: no automatic integration. Recommend a separate adapter experiment only for an explicitly supported subset; report game-version, character, state-import, mechanics and potion-policy limitations independently. A partial name match or a green unit test cannot establish full-state correctness or playing strength.

## Reproduction

Keep the pinned upstream checkout at ignored `vendor/sts2core-audit` and retain the historical raw trace directories. Review upstream Cargo.toml (no dependencies/build script), then:

```sh
cargo build --offline --release --lib --manifest-path vendor/sts2core-audit/Cargo.toml
rustc --edition=2021 -C panic=abort experiments/E114/probe.rs --extern sts2core=vendor/sts2core-audit/target/release/libsts2core.rlib -L dependency=vendor/sts2core-audit/target/release/deps -o artifacts/private/e114-probe
python3 scripts/audit_sts2core_e114.py
artifacts/private/e114-probe --synthetic
cargo test --offline --lib --manifest-path vendor/sts2core-audit/Cargo.toml
```

The Python audit reads historical committed manifests via `git show b7de162:...`; it does not require merging E113. Raw observations remain ignored. Results and source findings will be committed after execution.

## Iteration log

- `7509f1c`: upstream release library built offline in 5.70 seconds. The audit probe did not compile: upstream uses `panic=abort`, while standalone rustc defaults to unwind. The attempted Python audit therefore had no probe to invoke and produced no capability result. Correct the documented probe build to use the same panic strategy; preserve this failed harness attempt. No game or model execution occurred.
