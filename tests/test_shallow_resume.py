import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('resume',Path(__file__).resolve().parents[1]/'scripts/resume_shallow_e118.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ResumeTests(unittest.TestCase):
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
