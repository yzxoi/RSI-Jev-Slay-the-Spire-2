"""Synthetic identity/accounting contracts; no game outcome tests."""
import unittest
from scripts.audit_item_novelty_e151 import identity, aliases, canonical, extract


class ItemNoveltyTests(unittest.TestCase):
    def test_train_menu_alias_and_upgrade_share_base_identity(self):
        base = identity('card', {'id': 'CARD.BASH', 'name': 'Bash'})
        lookup = aliases([base, identity('card', {'name': 'Bash'})])
        self.assertEqual(canonical(base, lookup), canonical(identity('card', {'name': 'Bash+'}), lookup))
        self.assertNotEqual(canonical(base, lookup), canonical(identity('card', {'id': 'CARD.NEW', 'name': 'New'}), lookup))

    def test_owned_and_offered_are_distinct(self):
        obj = {'id': 'CARD.BASH', 'name': 'Bash', 'upgraded': True}
        own, vis, inv = extract({'player': {'deck': [obj, obj]},
            'potion': {'id': 'NEW_POTION', 'name': 'New Potion'},
            'bundles': [{'cards': [{'name': 'Offered Card'}]}]})
        self.assertEqual(len(own), 1)
        self.assertEqual(len(vis), 3)
        self.assertEqual(len(inv), 2)
        self.assertTrue(all(upgraded for _, upgraded in inv))

    def test_missing_and_ambiguous_identity_fail(self):
        with self.assertRaises(ValueError):
            identity('card', {})
        with self.assertRaises(ValueError):
            aliases([('card', 'CARD.ONE', 'Same'), ('card', 'CARD.TWO', 'Same')])
        with self.assertRaises(ValueError):
            canonical(('card', 'CARD.TWO', 'Same'), {('card', 'Same'): 'id:CARD.ONE'})


if __name__ == '__main__':
    unittest.main()
