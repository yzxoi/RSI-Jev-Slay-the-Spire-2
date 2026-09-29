import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('resume',Path(__file__).resolve().parents[1]/'scripts/resume_shallow_e118.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ResumeTests(unittest.TestCase):
    def test_mixed_transport_errors_share_one_cumulative_exit(self):
        ledger=m.base.Ledger(1);count=0
        for n,error in enumerate([m.TIMEOUT,'IncompleteRead: body ended','RemoteDisconnected: peer closed']):
            self.assertTrue(ledger.acquire(.1))
            count=m.settle_transport(ledger,.1,{'usage':{},'valid':False,'error':error},count)
            if n<2:
                self.assertIsNone(ledger.stop)
                self.assertTrue(ledger.acquire(.1))
                count=m.settle_transport(ledger,.1,{'usage':{'cost':.001},'valid':True,'error':None},count)
        self.assertEqual(count,3)
        self.assertIsNotNone(ledger.stop)
        self.assertAlmostEqual(ledger.unknown_reserved,.3)
        self.assertFalse(m.transport_error('http_403'))
        self.assertFalse(m.transport_error('invalid_json'))

    def test_continuation_preserves_failed_prefix_and_never_reissues_it(self):
        bank=m.base.make_bank();config='deepseek_low'
        c=m.CONFIGS[config]
        good={'response':{'model':c['canonical'],'provider':c['provider'],
            'choices':[{'finish_reason':'stop','message':{'content':'{"choice":"A"}'}}],
            'usage':{'cost':.000001}}}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            source=Path(tmp)/'source';source.mkdir();out=Path(tmp)/'out';out.mkdir()
            (source/'manifest.json').write_text(json.dumps({'bank_digest':m.digest(bank),'configurations':{config:c}}))
            with patch.object(m.base,'post',side_effect=[good,good,{'error':m.TIMEOUT}]) as initial:
                m.base.run_config(config,bank,'fake',source)
                self.assertEqual(initial.call_count,3)
            before=json.loads((source/config/'rows.json').read_text())
            with patch.object(m.base,'post',return_value=good) as continued:
                m.continue_config(config,bank,source,out,'fake')
                self.assertEqual(continued.call_count,101)
            after=json.loads((out/config/'rows.json').read_text())
            self.assertEqual(after[:3],before[:3])
            self.assertEqual(after[2]['error'],m.TIMEOUT)
            self.assertTrue(m.audit_config(config,bank,source,out)['passed'])

    def test_timeout_reserves_full_cost_without_retry_and_third_stops(self):
        l=m.base.Ledger(1)
        count=0
        for n in range(3):
            self.assertTrue(l.acquire(.1))
            count=m.settle_timeout(l,.1,{'usage':{},'valid':False,'error':m.TIMEOUT},count)
            self.assertAlmostEqual(l.unknown_reserved,.1*(n+1))
        self.assertEqual(count,3)
        self.assertIsNotNone(l.stop)
        self.assertFalse(l.acquire(.1))

    def test_provider_refusal_is_never_cleared(self):
        l=m.base.Ledger(1);l.acquire(.1)
        m.settle_timeout(l,.1,{'usage':{},'valid':False,'error':'http_403'},0)
        self.assertEqual(l.stop,'unknown_billing')
        self.assertFalse(l.acquire(.1))

    def test_invalid_rate_and_budget_still_apply(self):
        l=m.base.Ledger(1)
        l.calls=19;l.invalid=2
        l.acquire(.1)
        m.settle_timeout(l,.1,{'usage':{},'valid':False,'error':m.TIMEOUT},0)
        self.assertIsNotNone(l.stop)
        l=m.base.Ledger(.15);l.acquire(.1)
        m.settle_timeout(l,.1,{'usage':{},'valid':False,'error':m.TIMEOUT},0)
        self.assertFalse(l.acquire(.1))


if __name__=='__main__':unittest.main()
