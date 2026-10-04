"""Synthetic ownership/resource/freshness checks, not game outcomes."""
import unittest
from rsi.campaign_teacher import Ownership,permitted_state,validate


class CampaignTests(unittest.TestCase):
    def test_campaign_upgrade_and_battle_generated_choices_keep_correct_owner(self):
        owner=Ownership()
        self.assertEqual(owner.observe(dict(decision='card_select')),(False,False))
        self.assertEqual(owner.observe(dict(decision='combat_play')),(True,False))
        self.assertEqual(owner.observe(dict(decision='card_reward',from_event=True)),(True,False))
        self.assertEqual(owner.observe(dict(decision='card_select')),(True,False))
        self.assertEqual(owner.observe(dict(decision='card_reward',gold_earned=10,player=dict(hp=10))),(False,True))
        self.assertEqual(owner.observe(dict(decision='card_select')),(False,False))

    def test_reservation_filters_solver_input_not_native_inventory(self):
        state=dict(context=dict(room_type='Monster'),player=dict(hp=50,max_hp=80,
            potions=[dict(index=0,id='STRENGTH'),dict(index=1,id='FIRE')]))
        rules=[dict(potion_id='STRENGTH',until='Boss',release_hp_fraction=.25)]
        masked,blocked=permitted_state(state,rules)
        self.assertEqual(blocked,[0]);self.assertEqual(len(state['player']['potions']),2)
        self.assertEqual(masked['player']['potions'],[dict(index=1,id='FIRE')])
        state['player']['hp']=20
        self.assertEqual(permitted_state(state,rules)[1],[])
        state['player']['hp']=50;state['context']['room_type']='Boss'
        self.assertEqual(permitted_state(state,rules)[1],[])

    def test_stale_and_tactical_fields_rejected(self):
        req=dict(case='A0-000',run_id='test',seq=1,state_hash='fresh',
            state=dict(player=dict(potions=[])),choices=[dict(id='a001',action=dict(action='skip_card_reward'))])
        packet={k:req[k] for k in ('case','run_id','seq','state_hash')}
        packet.update(choice_id='a001',campaign_plan='Keep room for useful rewards.',potion_reservations=[])
        self.assertEqual(validate(packet,req),req['choices'][0])
        with self.assertRaises(ValueError):validate({**packet,'state_hash':'stale'},req)
        with self.assertRaises(ValueError):validate({**packet,'choice_id':'a999'},req)
        with self.assertRaises(ValueError):validate({**packet,'battle_actions':[]},req)
        with self.assertRaises(ValueError):validate({**packet,'potion_reservations':[
            dict(potion_id='missing',until='Boss',release_hp_fraction=.3)]},req)


if __name__=='__main__':unittest.main()
