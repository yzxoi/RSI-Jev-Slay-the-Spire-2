import unittest
from rsi.scenes import candidates,fingerprint
class SceneTests(unittest.TestCase):
    def test_claiming_card_reward_does_not_choose_card(self):
        s={'screen':'REWARD','available_actions':['claim_reward','collect_rewards_and_proceed'],'reward':{'rewards':[{'index':2,'claimable':True,'reward_type':'Card'}]}}
        self.assertEqual(candidates(s)[0]['action'],{'action':'claim_reward','option_index':2})
    def test_fingerprint_includes_reward_and_map(self):
        self.assertNotEqual(fingerprint({'screen':'MAP','map':{'x':1}}),fingerprint({'screen':'MAP','map':{'x':2}}))
    def test_shop_only_affordable_items(self):
        s={'screen':'SHOP','available_actions':['buy_card','close_shop_inventory'],'shop':{'cards':[{'index':4,'is_stocked':True,'enough_gold':False}]}}
        self.assertEqual([c['action']['action'] for c in candidates(s)],['close_shop_inventory'])
