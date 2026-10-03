"""Synthetic measurement/context tests; no strength or native-rule claims."""
import unittest
from rsi.continuation import FirstFight, FrozenProgram
from rsi.trace import digest
from scripts.pilot_continuation_e159 import ARMS, summarize


class ContinuationTests(unittest.TestCase):
    def test_first_clear_excludes_initial_and_potion_rewards_then_stays_frozen(self):
        meter=FirstFight()
        player=dict(hp=40,max_hp=80,gold=10,deck=[],potions=[])
        reward=dict(decision='card_reward',gold_earned=10,player=player)
        meter.observe(reward,[])
        self.assertIsNone(meter.result)
        combat=dict(decision='combat_play',player=player,context=dict(act=1,room_type='Elite'))
        meter.observe(combat,[])
        meter.observe({**reward,'from_event':True},[dict(action='potion')])
        self.assertIsNone(meter.result)
        plan=[dict(action='kill')]
        meter.observe(reward,plan)
        first=dict(meter.result)
        self.assertEqual(first['utility'],1.125)
        self.assertEqual(first['room_type'],'Elite')
        self.assertEqual(first['transition_hash'],digest(plan))
        meter.observe(dict(decision='game_over',victory=False,player=dict(hp=0)),plan*5)
        self.assertEqual(meter.result,first)

    def test_triggering_card_is_retained_across_chained_selection_menus(self):
        program=FrozenProgram(None)
        program.remember(dict(decision='combat_play'),dict(name='True Grit'))
        state=dict(decision='card_select',cards=[dict(index=0,type='Attack',stats=dict(damage=6)),
            dict(index=1,type='Status',stats={})])
        choices=[dict(name='Select',action=dict(action='select_cards',args=dict(card_index=i))) for i in (0,1)]
        first,meta=program.choose(state,choices,None)
        self.assertEqual(first,choices[1])
        self.assertEqual(meta['selection_origin'],'combat_play')
        program.remember(state,first)
        again,_=program.choose(state,choices,first)
        self.assertEqual(again,choices[1])
        self.assertEqual(program.parent['name'],'True Grit')

    def test_censored_full_suffix_cannot_pass_after_an_observed_first_clear(self):
        records=[]
        for i in range(30):
            records.append(dict(arms={a:dict(status='defeat',first_fight=dict(status='clear')) for a in ARMS},parity=[]))
        records[0]['arms']['actor_program']['status']='timeout'
        s=summarize(records,{},dict(pass_=True),1,1)
        self.assertFalse(s['complete'])
        self.assertFalse(s['continuation_gate'])
        self.assertNotIn('continuation_delta',s)


if __name__=='__main__':unittest.main()
