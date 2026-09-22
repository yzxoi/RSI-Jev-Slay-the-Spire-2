"""Legal headless candidates; no inferred target indices."""
from .engine import action


def combat_candidates(state):
    candidates = []
    for card in state.get("hand", []):
        if not card.get("can_play"):
            continue
        targeting = card.get("target_type")
        if targeting == "AnyEnemy":
            targets = [e["index"] for e in state.get("enemies", [])]
        elif targeting in ["Self", "None", "AllEnemies", "RandomEnemy"]:
            targets = [None]
        else:
            raise RuntimeError(f"Unimplemented target space: {targeting}")
        for target in targets:
            args = {"card_index": card["index"]}
            if target is not None:
                args["target_index"] = target
            candidates.append({"action": action("play_card", **args), "card_id": card["id"], "name": card["name"]})
    candidates.append({"action": action("end_turn"), "name": "End turn"})
    for i, candidate in enumerate(candidates):
        candidate["id"] = f"a{i:03}"
    return candidates


def model_state(state):
    # Keep the complete state in the trace; drop redundant upgrade previews from
    # the decision input. Current hand stats and character mechanics remain.
    result = dict(state)
    player = dict(result.get("player", {}))
    player["deck"] = [{k: v for k, v in c.items() if k != "after_upgrade"} for c in player.get("deck", [])]
    result["player"] = player
    return result
