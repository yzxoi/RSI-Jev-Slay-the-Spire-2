"""Synthetic guard contracts; real encounter evidence is registered separately."""
import unittest
from rsi.potion_applicability import defer_reason
from rsi.campaign_teacher import permitted_state


class ApplicabilityTests(unittest.TestCase):
    def state(self,hp=10,damage=0,block=0):
        return dict(player=dict(hp=hp,max_hp=80,block=block),
                    enemies=[dict(intents=[dict(total_damage=damage)])])

    def reason(self,s,ident,action='end_turn'):
        return defer_reason(s,dict(id=ident),dict(action=action))

    def test_block_is_reconsidered_before_lethal_end_turn(self):
        s=self.state(damage=15)
        self.assertEqual(self.reason(s,'BLOCK_POTION','play_card'),'finish_cards_before_block')
        self.assertIsNone(self.reason(s,'BLOCK_POTION'))
        s['player']['block']=15
        self.assertEqual(self.reason(s,'BLOCK_POTION'),'no_visible_unblocked_attack')
        s['player']['block']=0;s['player']['end_turn_block']=15
        self.assertEqual(self.reason(s,'BLOCK_POTION'),'no_visible_unblocked_attack')

    def test_regeneration_deficit_and_unknown_effects(self):
        self.assertEqual(self.reason(self.state(hp=80),'REGEN_POTION'),'no_current_healing_deficit')
        self.assertIsNone(self.reason(self.state(hp=79),'REGEN_POTION'))
        for ident in ('ASHWATER','SNECKO_OIL'):
            self.assertEqual(self.reason(self.state(),ident),'unverified_hand_transformation')
        self.assertIsNone(self.reason(self.state(),'FIRE_POTION'))

    def test_reservation_release_does_not_imply_usefulness(self):
        s=self.state(hp=80);s['context']=dict(room_type='Boss')
        s['player']['potions']=[dict(id='BLOCK_POTION',index=0)]
        masked,blocked=permitted_state(s,[dict(potion_id='BLOCK_POTION',until='Boss',release_hp_fraction=.25)])
        self.assertFalse(blocked)
        self.assertEqual(self.reason(masked,'BLOCK_POTION'),'no_visible_unblocked_attack')
