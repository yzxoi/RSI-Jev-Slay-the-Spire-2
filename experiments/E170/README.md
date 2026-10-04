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
