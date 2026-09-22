"""Narrow native encounter rules grounded in exported powers and card identities."""
def sandpit_rule(raw, choices):
    combat = raw.get("combat") or {}
    countdowns = [p["amount"] for e in combat.get("enemies", [])
                  if e.get("is_alive", True)
                  for p in e.get("powers", []) if p.get("power_id") == "SANDPIT_POWER"]
    if not countdowns or min(countdowns) > 2:
        return None
    countdown = min(countdowns)
    escapes = {c["index"]: c for c in combat.get("hand", [])
               if c.get("card_id") == "FRANTIC_ESCAPE" and c.get("playable")}
    legal = [c for c in choices if c["action"].get("action") == "play_card"
             and c["action"].get("card_index") in escapes]
    selected = min(legal, key=lambda c: escapes[c["action"]["card_index"]]["energy_cost"]) if legal else None
    return {"countdown": countdown, "selected": selected,
            "requires_expert": countdown <= 1 and selected is None,
            "reason": "Sandpit can kill regardless of HP/block; Frantic Escape increases its countdown."}
