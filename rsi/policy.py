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


def intent_damage(enemy):
    return sum(i.get("total_damage", i.get("damage", 0) * i.get("hits", 1)) or 0
               for i in enemy.get("intents") or [])


def computed_candidates(state, candidates):
    """Arithmetic on engine previews, explicitly not a state-transition simulator."""
    incoming = sum(intent_damage(e) for e in state.get("enemies", []))
    current_block = state.get("player", {}).get("block", 0)
    by_index = {e["index"]: e for e in state.get("enemies", [])}
    cards = {c["index"]: c for c in state.get("hand", [])}
    output = []
    for candidate in candidates:
        candidate = dict(candidate)
        command = candidate["action"]
        data = {"incoming_visible_damage": incoming, "current_block": current_block,
                "unblocked_visible_damage_now": max(0, incoming - current_block),
                "scope": "Static card previews only; ignores future draws, on-play triggers, changing modifiers, orbs, minions, damage caps, resurrection and end-turn powers."}
        if command["action"] == "play_card":
            card = cards[command["args"]["card_index"]]
            stats = card.get("stats") or {}
            block = max(0, stats.get("block", 0))
            data.update(block_preview=block, useful_block_now=min(block, max(0, incoming - current_block)),
                        energy_cost=card.get("cost", 0), energy_after=state.get("energy", 0) - max(0, card.get("cost", 0)))
            target = command["args"].get("target_index")
            previews = [p for p in card.get("damage_by_target") or [] if target is None or p["target_index"] == target]
            damage, prevented, kills = 0, 0, 0
            for preview in previews:
                enemy = by_index.get(preview["target_index"])
                if enemy is None:
                    continue
                total = preview.get("total_damage", preview.get("damage", 0) * preview.get("repeat", 1)) or 0
                health_damage = max(0, total - enemy.get("block", 0))
                damage += min(enemy["hp"], health_damage)
                if health_damage >= enemy["hp"]:
                    kills += 1
                    prevented += intent_damage(enemy)
            data.update(preview_hp_damage=damage, preview_kills=kills,
                        preview_attack_removed=prevented,
                        unblocked_visible_damage_after=max(0, incoming - prevented - current_block - block))
        candidate["computed"] = data
        output.append(candidate)
    return output


def greedy_choice(state, candidates):
    cards = {c["index"]: c for c in state.get("hand", [])}
    def score(candidate):
        if candidate["action"]["action"] == "end_turn":
            return 0
        features = candidate["computed"]
        card = cards[candidate["action"]["args"]["card_index"]]
        stats = card.get("stats") or {}
        value = (features["preview_hp_damage"] * .6 + features["useful_block_now"] * 1.15
                 + features["preview_kills"] * 8 + features["preview_attack_removed"]
                 + stats.get("cards", 0) * 2 + stats.get("vulnerablepower", 0) * 1.5
                 + stats.get("strengthpower", 0) * 4)
        # A fixed, deliberately simple numerical comparator. Unknown utility gets
        # a small positive value so setup cards are not always left unplayed.
        return (value + .2) / max(1, card.get("cost", 0))
    return max(candidates, key=score)
