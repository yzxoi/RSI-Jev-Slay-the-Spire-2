"""Synthetic domain and selection safety, not game outcomes."""
import unittest
from rsi.opening_subset import opening_domain,pick,rank


class OpeningSubsetTests(unittest.TestCase):
    def root(self,n=5):
        return dict(decision='card_select',context=dict(act=1,floor=2,room_type='Elite'),
            player=dict(relics=[dict(name='Gambling Chip')]),cards=[dict(index=i) for i in range(n)],
            min_select=0,max_select=999999999)

    def domain(self,s):
        return opening_domain(s,dict(action='select_map_node'),
            dict(decision='map_select',context=dict(act=1,floor=1,room_type='Map')))

    def test_bound_and_selection_scope_are_not_silently_relaxed(self):
        self.assertEqual(self.domain(self.root())['legal_subsets'],32)
        for change in ['large','mandatory','no_relic','shop']:
            s=self.root(6 if change=='large' else 5)
            if change=='mandatory':s['min_select']=1
            if change=='no_relic':s['player']['relics']=[]
            if change=='shop':s['context']['room_type']='Shop'
            with self.assertRaises(ValueError):self.domain(s)

    def test_true_clear_precedes_inventory_and_ties_are_deterministic(self):
        loss=dict(status='defeat',hp=0,potions=['x']*9,discard_indices=[])
        clear=dict(status='clear',hp=1,potions=[],discard_indices=[0])
        self.assertEqual(pick([loss,clear]),clear)
        tied=dict(clear,discard_indices=[])
        self.assertEqual(pick([clear,tied]),tied)
        self.assertEqual(pick([tied,clear]),tied)
        for status in ['timeout','error','unstarted']:
            with self.assertRaises(ValueError):rank(dict(clear,status=status))
        with self.assertRaises(ValueError):rank(dict(clear,error='Engine integrity failure'))
