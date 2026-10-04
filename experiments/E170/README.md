# E170 — Fresh-seed potion screen

Issue #327, conditional on E168 local gate passing (it did). Test generalization before another costly Astra-macro run. Eight frozen new seeds, Ironclad A0/A5 x4 each: e170_potions_Ironclad_A{0,5}_000..003. Typed E166 baseline vs frozen E168 combined. Both use exactly the same cautious program campaign decisions; no Astra/API calls, reservations or game edits. This is a cheap program-macro screen, not the user's ultimate Astra hybrid acceptance.

Each of16 attempts runs normally through every available reward/card/shop/event/rest/route until true game-over or a declared failure/cap. No selected rescue continuations, replacement seeds or retries. All16 traces independently replay. <=2400 actions and120 compute seconds/run,120s/replay,600s wall, four workers. Manifest freezes exact policy source hashes and runtime.

Gate: all genuine terminals and exact replays; no illegal action; no negative pair under (victory, completed acts, cleared fights); >=2 improving source-seed pairs and >=4 seeds exposing a guarded potion. All failures and lack of exposure reported. HP/inventory are not silently converted to a win rate. No default promotion from this small screen even if it passes. Failure stops recipe promotion and motivates a specific separate diagnosis.

The episode function accepts an optional explicit program instance for this experiment. Its default remains FrozenProgram. E167 routing applies equally to both arms; no monkeypatch or cross-thread policy state.

```sh
python3 -m unittest discover -s tests -p test_campaign_teacher.py
python3 scripts/validate_fresh_potions_e170.py plan --output experiments/E170/plan-v1.json
# commit frozen plan
python3 scripts/validate_fresh_potions_e170.py evaluate --plan experiments/E170/plan-v1.json --output artifacts/runs/e170-evaluation-v1.json
```

## v1 result and decision

Tested `dc01b28` (implementation `4e99be6`). Six routing/teacher tests pass. All16 full attempts reached real defeat, all16 independent replays match,32 bundles pass, no illegal actions, no teacher/API calls,55.947s. No caps, errors, replacement seeds or rollbacks.

Both arms:0/8 full wins and0/8 completed acts. Seven seeds die at act1 floor17 Boss; A5-001 dies at floor12 Elite. Completed battles are identical across arms: A0 [11,7,8,7], A5 [8,7,6,7]. Thus zero positive or negative progress pairs.

Only A0-000 (Ashwater) and A5-003 (Block Potion) expose guarded potion types. Their actions differ but final progress ties. The other six pairs have identical full transition hashes. Exposure2/8 misses the >=4 coverage requirement; do not interpret this as proving no local effect. The new-seed screen fails both improvement and exposure gates, despite integrity passing. This program-macro screen is not evidence about fresh Astra-built decks.

Decision: close PR unmerged, preserve branch/results, do not promote or expand this fixed recipe. E168's opt-in known-entry policy/evidence remains available on main; default unchanged. Next registered distinct hypothesis is E169/#326 typed opening-subset search. It remains unexecuted; no claim that changing Gambling Chip selection rescues E167.
