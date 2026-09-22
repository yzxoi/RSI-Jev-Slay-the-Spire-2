import copy
import unittest
from rsi.mcp import live_candidates, stable_fingerprint, is_pre_execution_rejection, proposal_is_current


class MCPTests(unittest.TestCase):
    def test_only_audited_pre_execution_error_is_recoverable(self):
        error = {"error": {"code": "invalid_action", "status_code": 409,
                           "message": "Action is not in available_actions."}, "available_actions": ["save_and_quit"]}
        self.assertTrue(is_pre_execution_rejection("act", error))
        self.assertFalse(is_pre_execution_rejection("get_raw_game_state", error))
        error["error"]["message"] = "Action timed out after execution"
        self.assertFalse(is_pre_execution_rejection("act", error))
        self.assertFalse(is_pre_execution_rejection("act", {"status": "pending"}))
        gate = {"error": {"code": "invalid_action", "status_code": 409, "message": "Action is not available in the current state.", "details": {"action": "play_card", "screen": "COMBAT"}}}
        self.assertTrue(is_pre_execution_rejection("act", gate))
        gate["error"]["details"]["action"] = "buy_card"
        self.assertFalse(is_pre_execution_rejection("act", gate))

    def test_proposal_must_remain_actionable_even_with_unchanged_cards(self):
        before = {"available_actions": ["end_turn"], "combat": {"action_readiness": {"can_use_combat_actions": True}}}
        selected = {"action": {"action": "end_turn"}}
        self.assertTrue(proposal_is_current(before, before, selected))
        after = copy.deepcopy(before)
        after["combat"]["action_readiness"]["can_use_combat_actions"] = False
        self.assertFalse(proposal_is_current(before, after, selected))

    def test_live_target_indices_and_admin_actions(self):
        raw = {"available_actions": ["play_card", "end_turn", "save_and_quit", "discard_potion", "use_potion"],
               "combat": {"hand": [{"index": 3, "card_id": "STRIKE", "name": "Strike", "playable": True,
                                     "requires_target": True, "valid_target_indices": [4], "target_index_space": "enemies"},
                                    {"index": 7, "playable": False}]},
               "run": {"potions": [{"index": 2, "potion_id": "WEAK", "name": "Weak", "can_use": True,
                                     "requires_target": True, "valid_target_indices": [4], "target_index_space": "enemies"}]}}
        actions = [c["action"] for c in live_candidates(raw)]
        self.assertEqual(actions, [{"action": "play_card", "card_index": 3, "target_index": 4},
                                  {"action": "use_potion", "option_index": 2, "target_index": 4},
                                  {"action": "end_turn"}])
        raw["available_actions"] = ["save_and_quit"]
        self.assertEqual(live_candidates(raw), [])

    def test_stale_state_detection_ignores_only_readiness(self):
        before = {"run_id": "x", "screen": "COMBAT", "combat": {"hand": [{"index": 0, "name": "Strike"}], "action_readiness": {"ready": False}}}
        after = copy.deepcopy(before)
        after["combat"]["action_readiness"] = {"ready": True}
        self.assertEqual(stable_fingerprint(before), stable_fingerprint(after))
        after["combat"]["hand"][0]["name"] = "Defend"
        self.assertNotEqual(stable_fingerprint(before), stable_fingerprint(after))
