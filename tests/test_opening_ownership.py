"""Synthetic lifecycle contracts, not battle strength evidence."""
import unittest
from rsi.campaign_teacher import Ownership


def state(phase,room='Elite',floor=2,**kw):
    return dict(decision=phase,context=dict(act=1,floor=floor,room_type=room),player=dict(hp=47),**kw)


class OpeningTests(unittest.TestCase):
    def test_opening_generated_reward_and_postcombat_pickup(self):
        o=Ownership()
        self.assertEqual(o.observe(state('map_select','Map',1)),(False,False))
        for s in [state('card_select'),state('card_reward',from_event=True),state('combat_play')]:
            self.assertEqual(o.observe(s),(True,False))
        self.assertEqual(o.observe(state('potion_reward')),(False,True))
        self.assertEqual(o.observe(state('card_select')),(False,False))
        self.assertEqual(o.observe(state('card_reward',gold_earned=0)),(False,False))

    def test_campaign_menus_and_event_battle(self):
        for room,phase in [('Event','event_choice'),('RestSite','rest_site'),('Shop','shop')]:
            o=Ownership();o.observe(state(phase,room))
            self.assertEqual(o.observe(state('card_select',room)),(False,False))
        o=Ownership();o.observe(state('event_choice','Event'))
        self.assertEqual(o.observe(state('card_select','Monster')),(True,False))

    def test_detached_opening_rejects_and_defeat_is_not_clear(self):
        with self.assertRaisesRegex(ValueError,'Unbound'):Ownership().observe(state('card_select'))
        o=Ownership();o.observe(state('combat_play'))
        self.assertEqual(o.observe(state('game_over')),(False,False))
