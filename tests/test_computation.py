import unittest
from rsi.policy import computed_candidates, combat_candidates, intent_damage, greedy_choice


class ComputationTests(unittest.TestCase):
    def test_multihit_total_is_not_multiplied_twice(self):
        self.assertEqual(intent_damage({"intents": [{"damage": 5, "hits": 3, "total_damage": 15}]}), 15)

    def test_target_specific_kill_and_effective_block(self):
        state = {"energy": 3, "player": {"block": 2}, "enemies": [
            {"index": 0, "hp": 8, "block": 1, "intents": [{"damage": 9}]},
            {"index": 1, "hp": 20, "block": 0, "intents": [{"damage": 2}]}],
            "hand": [{"index": 0, "id": "strike", "name": "Strike", "target_type": "AnyEnemy", "cost": 1, "can_play": True,
                      "stats": {"damage": 6}, "damage_by_target": [{"target_index": 0, "damage": 9}, {"target_index": 1, "damage": 6}]},
                     {"index": 1, "id": "defend", "name": "Defend", "target_type": "Self", "cost": 1, "can_play": True,
                      "stats": {"block": 15}}]}
        candidates = computed_candidates(state, combat_candidates(state))
        self.assertEqual(candidates[0]["computed"]["preview_kills"], 1)
        self.assertEqual(candidates[0]["computed"]["unblocked_visible_damage_after"], 0)
        self.assertEqual(candidates[2]["computed"]["useful_block_now"], 9)
        self.assertEqual(greedy_choice(state, candidates)["action"]["args"]["target_index"], 0)
