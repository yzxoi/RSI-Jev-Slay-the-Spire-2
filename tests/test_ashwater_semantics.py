"""Synthetic semantic checks; no game-state editing in outcome evaluation."""
import unittest
from rsi.ppo_actions import complete_choices
from rsi.teacher import selection_choice
from rsi.battle_search import CONTROL


class AshwaterSemantics(unittest.TestCase):
    def test_optional_exhaust_preserves_engine_and_zero_preview_attack(self):
        cards=[dict(index=0,id='CARD.HELLRAISER',name='Hellraiser',type='Power',stats=None),
               dict(index=1,id='CARD.PERFECTED_STRIKE',name='Perfected Strike',type='Attack',stats={'calculateddamage':0}),
               dict(index=2,id='CARD.WOUND',name='Wound',type='Status',stats=None)]
        state=dict(decision='card_select',cards=cards,min_select=0,max_select=3,
                   player=dict(potions=[]))
        choices=complete_choices(state)
        parent=dict(name='Ashwater',details=dict(id='ASHWATER'))
        legacy=selection_choice(state,choices,CONTROL,parent)
        fixed=selection_choice(state,choices,{**CONTROL,'typed_ashwater':True},parent)
        self.assertIn('0',legacy['action']['args']['indices'].split(','))
        self.assertEqual(fixed['action']['args']['indices'],'2')
        state['cards']=cards[:2];state['max_select']=2
        fixed=selection_choice(state,complete_choices(state),{**CONTROL,'typed_ashwater':True},parent)
        self.assertIn(fixed['action']['action'],('skip_select','select_cards'))
        self.assertFalse(fixed['action']['args'].get('indices'))

    def test_generated_power_selection_keeps_positive_polarity(self):
        state=dict(decision='card_select',min_select=1,max_select=1,player=dict(potions=[]),
            cards=[dict(index=0,id='CARD.POWER',name='Power',type='Power',stats=None),
                   dict(index=1,id='CARD.WOUND',name='Wound',type='Status',stats=None)])
        parent=dict(name='Power Potion',details=dict(id='POWER_POTION'))
        choices=complete_choices(state)
        self.assertEqual(selection_choice(state,choices,CONTROL,parent),
                         selection_choice(state,choices,{**CONTROL,'typed_ashwater':True},parent))
        with self.assertRaises(ValueError):
            selection_choice(state,choices,{**CONTROL,'typed_ashwater':True},
                             dict(name='Ashwater',details=dict(id='ASHWATER')))
