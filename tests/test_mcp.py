import copy
import unittest
from rsi.mcp import live_candidates, stable_fingerprint


class MCPTests(unittest.TestCase):
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
