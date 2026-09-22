# E001 — Local headless compatibility

Issue: #2. Hypothesis: the pinned engine can start all five characters at ascension 10 and reach the end of their first natural combat without protocol failure.

Fixed sample: seed `compat_001`; Ironclad, Silent, Defect, Regent, Necrobinder; ascension 10. Policy: first playable card, first enemy, skip card rewards. This is an execution baseline, not a strong policy.

Decision rule: retain the engine adapter if all five executions end the first fight or reach normal defeat; report engine errors separately. No full-run or general mechanics-fidelity claim.

Iteration 1: pin upstream and SDK; build only local copies of game binaries; implement bounded JSON transport and persist wire traces. Existing system SDK is 7.0.317, so .NET 9 is installed inside ignored `.tools` without changing global installation.

Commands:

```sh
python3 scripts/setup_headless.py
python3 -m rsi.compatibility --output experiments/E001/results-v1.json
```

Result: implementation `21154b4`; SDK 9.0.318 build completed with 10 upstream nullable warnings and zero errors. All five A10 first combats completed (5/5); no engine/protocol failures. Runtime 1.093–1.193 seconds per process including startup. Final HP: Ironclad 44, Silent 26, Defect 52, Regent 40, Necrobinder 43. See `results-v1.json` for original DLL hash and trace digests.

Decision: merge the isolated engine adapter and execution probe. These are five opening battles, not full runs or proof of exact simulation fidelity.
