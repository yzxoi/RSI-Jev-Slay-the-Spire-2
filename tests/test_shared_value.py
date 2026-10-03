"""Synthetic encoder contracts, not gameplay evidence."""
import copy
import unittest
import numpy as np
from rsi.shared_value import entity, shared_encode, ValueMLP


class SharedValueTests(unittest.TestCase):
    def test_numeric_channels_shared_across_card_identities(self):
        a = dict(id='CARD.A', name='One', type='Attack', cost=1, stats={'damage': 9})
        b = {**a, 'id': 'CARD.B', 'name': 'Two'}
        np.testing.assert_array_equal(entity(a, 'card')[:40], entity(b, 'card')[:40])
        b['stats'] = {'damage': 12}
        self.assertGreater(entity(b, 'card')[2], entity(a, 'card')[2])

    def test_permutation_and_index_invariance_preserve_counts(self):
        cards = [dict(id='A', name='A', cost=1, index=3, stats={'damage': 6}),
                 dict(id='B', name='B', cost=2, index=0, stats={'block': 8})]
        s = dict(decision='combat_play', hand=cards, player={'deck': cards})
        old = np.zeros(540, dtype=np.float32)
        a = shared_encode(s, old)
        shuffled = copy.deepcopy(s)
        shuffled['hand'].reverse()
        shuffled['player']['deck'].reverse()
        shuffled['hand'][0]['index'] = 999
        shuffled['seed'] = 'do-not-encode'
        np.testing.assert_allclose(a, shared_encode(shuffled, old), atol=1e-6)
        doubled = copy.deepcopy(s)
        doubled['hand'] += cards
        self.assertGreater(shared_encode(doubled, old)[36], a[36])
        self.assertEqual(len(a), 540)

    def test_shapes_empty_menus_and_model_size(self):
        s = {'decision': 'event_choice', 'options': [], 'player': {}}
        self.assertTrue(np.isfinite(shared_encode(s, np.zeros(540))).all())
        self.assertEqual(sum(p.numel() for p in ValueMLP().parameters()), 86529)
        with self.assertRaises(ValueError):
            entity({'stats': {'damage': float('nan')}}, 'card')


if __name__ == '__main__':
    unittest.main()
