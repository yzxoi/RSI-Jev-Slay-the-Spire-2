import unittest
from rsi.full import macro_candidates

class FullTests(unittest.TestCase):
    def test_reward_skip_respects_engine(self):
        s={'decision':'card_reward','cards':[{'index':4}],'can_skip':False}
        self.assertEqual([c['action']['action'] for c in macro_candidates(s)],['select_card_reward'])
        self.assertEqual(macro_candidates(s)[0]['action']['args'],{'card_index':4})
    def test_selection_count_and_current_indices(self):
        s={'decision':'card_select','cards':[{'index':2},{'index':5},{'index':9}],'min_select':2,'max_select':2}
        self.assertEqual([c['action']['args']['indices'] for c in macro_candidates(s)],['2,5','2,9','5,9'])
    def test_shop_affordability_stock_and_once_only_removal(self):
        s={'decision':'shop','player':{'gold':80},'cards':[{'index':0,'cost':81,'is_stocked':True},{'index':3,'cost':60,'is_stocked':True},{'index':4,'cost':1,'is_stocked':False}],'card_removal_cost':75}
        self.assertEqual([c['action']['action'] for c in macro_candidates(s,{'removed_here':True})],['buy_card','leave_room'])
