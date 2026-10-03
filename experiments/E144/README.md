# E144 — Route teacher collection bias

Issue271.

The full-run neural experiment uses the difficulty-oriented E120 macro teacher: forced first Elite, first offered card/reward in generic phases, leave shops. E143 isolates search-to-actor transfer; it does not address this full-run teaching target. Register a distinct cheap ablation before adding more RL: keep combat and all other macro choices fixed, remove only the forced-Elite override so existing fixed_macro route ranking handles routing.

Use30fixed NEW training-only configurations (5heroes × A0/A5/A10 ×2) seed e144_train_{hero}_A{asc}_{i:02}; paired elite-first and existing route-policy arms (60complete attempts),180s/2400actions,8workers,900s total. No model updates or evaluation/final seeds. Retain every run/defeat, map choice and battle entry; replay first index00A0 ofeachhero ineacharm (10full histories). Gate: all terminal/replays exact, route arm improves Act2 arrival by>=3/30 with no reduction inIroncladA0Act2 count; report Act3/fullvictories and hero×act×difficulty coverage separately. Newlate-game states enter train bank only, no claim this heuristics arm meets network-only acceptance. If gate fails keep evidence and do not replace teacher; next whole-act RL experiment must declare a new objective rather than blindly imitate this teacher. This is a proposal, not executed.

Implementation uses the existing fixed_macro routing, without cautious_route or new ranking features. Only map choices can differ from the elite-first arm; same complete combat/potion/card-select planner and identical nonmap macro decisions. Add an opt-in macro callback to run_env; default stays unchanged and callbacks remain classified as programmatic planning, not network calls.

Command: `python3 scripts/ablate_route_e144.py --output artifacts/runs/e144-route-v1.json`.

## Result and decision

Tested997d023. Threefull-run boundary/menu unit tests passed.60natural fullruns all legitimate defeats;10preselected full histories replayed exactly,70rawbundles audited;62.805s. Elite-priority arm1/30Act2arrival; existing route ranking2/30; neitherAct3arrival, neitherIroncladA0Act2arrival. Collection gate fails (needed+3/30, observed+1/30). Allselected seeds/characters retained; no errors/caps.

Merge the optional one-factor experiment/callback and evidence; do not replace the default collection teacher or training policy. Forcingelites is a concrete objective mismatch, but removing it alone did not meet the practical coverage gate. First-card rewards/leave-shop choices and actual combat/card semantics remain untested separate hypotheses, not proven causes. New60train traces/battle-entry offsets are retained without silently mixing them into any prior completed training. No acceptance seed, model update or inference GPU work here.
