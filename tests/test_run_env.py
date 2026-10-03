import unittest
from rsi.run_env import legal_choices,run_outcome


class RunBoundaryTests(unittest.TestCase):
    def test_rewards_are_not_full_run_victories(self):
        for decision in ('card_reward','potion_reward','map_select','rest_site','card_select'):
            self.assertIsNone(run_outcome({'decision':decision,'context':{'room_type':'Boss'}}))
        self.assertEqual(run_outcome({'decision':'game_over','victory':True}),'victory')
        self.assertEqual(run_outcome({'decision':'game_over','victory':False}),'defeat')

    def test_shop_removal_history_keeps_exit_and_other_legal_choices(self):
        state={'decision':'shop','player':{'gold':100,'has_open_potion_slots':True},'cards':[],
               'relics':[],'potions':[],'card_removal_cost':75}
        before=legal_choices(state,{})
        after=legal_choices(state,{'removed_here':True})
        self.assertIn('remove_card',[c['action']['action'] for c in before])
        self.assertEqual([c['action']['action'] for c in after],['leave_room'])

    def test_disabled_event_choices_never_reach_network(self):
        state={'decision':'event_choice','options':[{'index':0,'is_locked':True},{'index':1,'is_enabled':False},{'index':2}]}
        self.assertEqual([c['action']['args'] for c in legal_choices(state,{})],[{'option_index':2}])
