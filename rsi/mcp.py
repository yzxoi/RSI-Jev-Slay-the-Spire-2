"""Native STS2 Streamable HTTP MCP client, with every RPC preserved."""
import json
import urllib.request


class ActionNotAccepted(RuntimeError):
    """Native MCP rejected legality before calling the game action bridge."""


def is_pre_execution_rejection(name, data):
    error = data.get("error") or {}
    return (name == "act" and error.get("code") == "invalid_action"
            and error.get("message") == "Action is not in available_actions."
            and error.get("status_code") == 409
            and isinstance(data.get("available_actions"), list))


class MCP:
    def __init__(self, url, trace):
        self.url, self.trace, self.sequence = url, trace, 0
        self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                "clientInfo": {"name": "rsi-jev", "version": "0.1"}})
        self.rpc("notifications/initialized", {}, notification=True)

    def rpc(self, method, params, notification=False):
        self.sequence += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = self.sequence
        self.trace.write("mcp_request", body)
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read()
            result = json.loads(payload) if payload else {}
        except Exception as exc:
            self.trace.write("mcp_transport_failure", {"method": method, "error": str(exc),
                                                       "delivery_may_be_uncertain": method == "tools/call" and params.get("name") == "act"})
            raise  # Never automatically resend a potentially accepted action.
        self.trace.write("mcp_response", result)
        if result.get("error"):
            raise RuntimeError(f"MCP RPC error: {result['error']}")
        return result.get("result", {})

    def call(self, name, arguments=None):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        blocks = [c for c in result.get("content", []) if c.get("type") == "text"]
        if not blocks:
            raise RuntimeError(f"MCP {name} returned no structured text")
        data = json.loads(blocks[0]["text"])
        if is_pre_execution_rejection(name, data):
            raise ActionNotAccepted(f"MCP action was not accepted: {data}")
        if result.get("isError") or data.get("error") or data.get("status") == "failed":
            raise RuntimeError(f"MCP {name} failed: {data}")
        return data


def live_candidates(raw):
    legal = raw.get("available_actions", [])
    candidates = []
    if "play_card" in legal:
        for card in (raw.get("combat") or {}).get("hand", []):
            if not card.get("playable"):
                continue
            targets = card.get("valid_target_indices", []) if card.get("requires_target") else [None]
            for target in targets:
                command = {"action": "play_card", "card_index": card["index"]}
                if target is not None:
                    command["target_index"] = target
                candidates.append({"action": command, "name": card["name"], "card_id": card["card_id"],
                                   "rules": card.get("resolved_rules_text"), "target_space": card.get("target_index_space")})
    if "use_potion" in legal:
        for potion in (raw.get("run") or {}).get("potions", []):
            if not potion.get("can_use"):
                continue
            targets = potion.get("valid_target_indices", []) if potion.get("requires_target") else [None]
            for target in targets:
                command = {"action": "use_potion", "option_index": potion["index"]}
                if target is not None:
                    command["target_index"] = target
                candidates.append({"action": command, "name": potion["name"], "potion_id": potion["potion_id"],
                                   "target_space": potion.get("target_index_space")})
    if "end_turn" in legal:
        candidates.append({"action": {"action": "end_turn"}, "name": "结束回合"})
    for i, c in enumerate(candidates):
        c["id"] = f"a{i:03}"
    return candidates


def stable_fingerprint(raw):
    from .trace import digest
    combat = dict(raw.get("combat") or {})
    combat.pop("action_readiness", None)
    return digest({"run_id": raw.get("run_id"), "screen": raw.get("screen"), "turn": raw.get("turn"),
                   "combat": combat, "run": raw.get("run"), "selection": raw.get("selection")})


def proposal_is_current(before, fresh, selected):
    return (bool((fresh.get("combat") or {}).get("action_readiness", {}).get("can_use_combat_actions"))
            and stable_fingerprint(before) == stable_fingerprint(fresh)
            and selected["action"] in [c["action"] for c in live_candidates(fresh)])
