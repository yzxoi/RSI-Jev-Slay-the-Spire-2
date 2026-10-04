"""Synthetic protocol integration checks, not wins."""
import unittest
from types import SimpleNamespace
from rsi.campaign_teacher import CampaignTeacher
from rsi.engine import action
from rsi.macro_transaction import Transaction


class Transactions(unittest.TestCase):
    def test_factored_deck_selection_uses_fresh_menu_index(self):
        trace=SimpleNamespace(directory=SimpleNamespace(name='synthetic'),write=lambda *args:None)
        teacher=CampaignTeacher(trace,'synthetic',None,None,0,transactions=True);teacher.plan='Upgrade Bash.'
        card=dict(id='CARD.BASH',name='Bash',cost=2,type='Attack',upgraded=False,stats={'damage':8})
        player=dict(deck=[card],potions=[],relics=[],gold=0,hp=50,max_hp=80,potion_capacity=2)
        before=dict(decision='rest_site',context={'floor':1},player=player)
        first=dict(action=action('choose_option',option_index=1),details={'option_id':'SMITH'})
        teacher.transaction=Transaction(before,first,[dict(kind='select_deck_card',index=0,potion_reservations=None)])
        after=dict(decision='card_select',context={'floor':1},player=player,cards=[dict(card,index=7)],min_select=1,max_select=1)
        teacher.accepted(before,first,after)
        chosen,owner,_=teacher.automatic(after,[])
        self.assertEqual(chosen['action'],action('select_cards',indices='7'))
        self.assertEqual(owner,'campaign_transaction')
        self.assertEqual(teacher.count,0)

    def test_changed_transition_requires_fresh_guidance(self):
        trace=SimpleNamespace(directory=SimpleNamespace(name='synthetic'),write=lambda *args:None)
        teacher=CampaignTeacher(trace,'synthetic',None,None,0,transactions=True);teacher.plan='Upgrade.'
        card=dict(id='CARD.BASH',name='Bash',cost=2,type='Attack')
        before=dict(decision='rest_site',context={'floor':1},player=dict(deck=[card],potions=[],relics=[],gold=0,hp=50,max_hp=80,potion_capacity=2))
        first=dict(action=action('choose_option',option_index=1),details={'option_id':'SMITH'})
        teacher.transaction=Transaction(before,first,[dict(kind='select_deck_card',index=0,potion_reservations=None)])
        after={**before,'context':{'floor':2}}
        teacher.accepted(before,first,after)
        self.assertIsNone(teacher.automatic(after,[]))
        self.assertIsNone(teacher.transaction)


if __name__=='__main__':unittest.main()
