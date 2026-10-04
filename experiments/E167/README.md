# E167 — Battle-opening ownership

Issue #321. Hypothesis: track the room entry before `combat_play`, so opening relic selections stay with the fixed battle executor. Baseline is main at a45b794 (E160 Ownership); all other battle choices remain FrozenProgram/E159.

The source serializes pending card selections before checking `CombatManager.IsInProgress`; it does not export an explicit selection owner. The controller now recognizes an observed map/event-to-combat-room transition, retains ownership through generated cards, and does not reopen a completed room during reward pickups. An unbound opening fails closed. No engine patch.

Independent audit uses raw triggering commands and preceding/following stable phases, with the unfinished E165 306-command opening explicitly labelled from map entry, Elite context, Gambling Chip relic text and engine log. It never reads the classifier's `combat_active` flag. This is independent wire/lifecycle evidence, not a newly exposed engine lifecycle API. Unknown sequences fail audit.

## Frozen evaluation

All 12 E160/E165 original traces, every card_select/generated-card boundary, exact wire hashes and expected labels in plan-v1.json. Replay each original prefix in a separate engine; compare all responses. Continue only E165 A5-000's natural Gambling Chip opening with FrozenProgram until first actual battle boundary, then independently replay. The historical E165 run remains interrupted. No HP/reward changes, no teacher/API requests, no full-run claim.

Synthetic lifecycle tests: opening, generated reward, completed-room pickup, event, upgrade, shop removal, event battle, detached ambiguous selection, defeat. Require zero incorrect labels, no extra clear counts, zero illegal actions, exact replay fidelity, and no campaign request at the opening. <=600s total; <=120s/300 actions for the diagnostic.

```sh
python3 -m unittest discover -s tests -p test_opening_ownership.py
python3 -m unittest discover -s tests -p test_campaign_teacher.py
python3 scripts/validate_ownership_e167.py plan --output experiments/E167/plan-v1.json
# commit frozen plan before evaluate
python3 scripts/validate_ownership_e167.py evaluate --plan experiments/E167/plan-v1.json --output artifacts/runs/e167-evaluation-v1.json
```

Implementation and subsequent result commits preserve each iteration. Runtime/version/code SHA are in each manifest. The gate establishes routing compatibility only; opening discard quality is deliberately unchanged.

## v1 result and decision

Tested SHA `52a1214` (implementation `c0bb341`). Six tests passed. All 104 selection labels matched (59 battle, 45 campaign); the independent request audit found the one original E165 seq38 misroute despite its old combat_active=false flag. All 12 original prefixes and the new diagnostic reproduced exactly; 14 trace bundles passed audit. No extra clear boundaries, illegal commands or teacher/API calls. Wall 117.410s.

The 306-command natural opening continued for 19 program actions and ended in **defeat at 0 HP**. This compatibility fix does not rescue the encounter, establish selection quality, or complete the original interrupted run. Raw trace and replay hashes are in evaluation-v1.json.

Merge the routing/audit fix because the registered compatibility gate passes. Do not promote a battle-strength claim. Keep the failure available for a separate selection-quality hypothesis.
