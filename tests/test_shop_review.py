import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from rsi import campaign
from rsi.shop_review import funded_shop_exit_review


FIXTURE = json.loads((Path(__file__).resolve().parents[1] /
                      'experiments/E068/frozen-shop-floor20.json').read_text())


class FundedShopReviewTest(unittest.TestCase):
    def test_frozen_exit_and_bypass_cases(self):
        raw = FIXTURE['state']
        proposal = FIXTURE['jev_proposal']
        report = funded_shop_exit_review(raw, proposal)
        self.assertTrue(report['review'])
        self.assertEqual([item['relic_id'] for item in report['affordable_relics']],
                         ['PARRYING_SHIELD', 'RED_SKULL', 'WING_CHARM'])
        self.assertFalse(funded_shop_exit_review(raw, proposal, explicit_choice=True)['review'])
        self.assertFalse(funded_shop_exit_review(raw, {'action': 'buy_relic', 'option_index': 0})['review'])
        self.assertFalse(funded_shop_exit_review(raw, proposal, purchases_here=1)['review'])
        low = copy.deepcopy(raw)
        low['run']['gold'] = 249
        self.assertFalse(funded_shop_exit_review(low, proposal)['review'])
        bought = copy.deepcopy(raw)
        bought['shop']['relics'][0]['is_stocked'] = False
        self.assertFalse(funded_shop_exit_review(bought, proposal)['review'])
        no_relic = copy.deepcopy(raw)
        no_relic['shop']['relics'] = []
        self.assertFalse(funded_shop_exit_review(no_relic, proposal)['review'])

    def test_controller_pauses_before_act_delivery(self):
        calls = []
        raw = FIXTURE['state']

        class FakeMCP:
            def __init__(self, url, trace):
                pass

            def call(self, name, args=None):
                calls.append(name)
                if name == 'health_check':
                    return {'status': 'ready', 'play_running': False}
                if name == 'get_raw_game_state':
                    return copy.deepcopy(raw)
                raise AssertionError(f'Unexpected native action: {name}')

        class FakeJev:
            def __init__(self, budget):
                pass

            def choose(self, context, candidates, trace):
                return next(c for c in candidates if c['action']['action'] == 'close_shop_inventory'), {}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            argv = ['campaign', '--expected-run-id', raw['run_id'], '--max-actions', '1',
                    '--output', str(output), '--execute', '--review-funded-shop']
            with patch.object(campaign, 'ROOT', Path(directory)), patch.object(campaign, 'MCP', FakeMCP), \
                 patch.object(campaign, 'Jev', FakeJev), \
                 patch.object(campaign, 'version_manifest', return_value={'code_commit': 'test', 'tracked_dirty': False}), \
                 patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
                campaign.main()
            result = json.loads(output.read_text())['result']
            self.assertEqual(result['status'], 'expert_required')
            self.assertEqual(result['actions'], 0)
            self.assertEqual(result['shop_reviews'], 1)
            self.assertNotIn('act', calls)


if __name__ == '__main__':
    unittest.main()
