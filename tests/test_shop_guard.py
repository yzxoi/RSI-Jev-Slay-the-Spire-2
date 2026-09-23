import json
from pathlib import Path
import unittest

from rsi.shop_guard import funded_relic_candidates


class FundedShopGuardTest(unittest.TestCase):
    def test_frozen_native_shop_exposes_only_legal_relics(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] /
                              'experiments/E066/frozen-shop-floor20.json').read_text())
        choices, report = funded_relic_candidates(fixture['state'], fixture['candidates'], 0)
        self.assertTrue(report['triggered'])
        self.assertEqual({c['details']['relic_id'] for c in choices},
                         {'PARRYING_SHIELD', 'RED_SKULL', 'WING_CHARM'})
        self.assertTrue(all(c['action']['action'] == 'buy_relic' and
                            c['details']['price'] <= fixture['state']['run']['gold'] for c in choices))
        after_purchase, report = funded_relic_candidates(fixture['state'], fixture['candidates'], 1)
        self.assertFalse(report['triggered'])
        self.assertEqual(after_purchase, fixture['candidates'])

    def test_headless_budget_and_affordability(self):
        state = {'decision': 'shop', 'player': {'gold': 260}}
        choices = [
            {'action': {'action': 'buy_relic', 'args': {'relic_index': 0}},
             'details': {'name': 'Affordable', 'cost': 240, 'is_stocked': True}},
            {'action': {'action': 'buy_relic', 'args': {'relic_index': 1}},
             'details': {'name': 'Too costly', 'cost': 300, 'is_stocked': True}},
            {'action': {'action': 'leave_room'}, 'details': None},
        ]
        kept, report = funded_relic_candidates(state, choices, 0)
        self.assertTrue(report['triggered'])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]['details']['name'], 'Affordable')
        state['player']['gold'] = 249
        kept, report = funded_relic_candidates(state, choices, 0)
        self.assertFalse(report['triggered'])
        self.assertEqual(kept, choices)


if __name__ == '__main__':
    unittest.main()
