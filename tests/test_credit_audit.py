"""Synthetic diagnostic math; not game-strength tests."""
import unittest
from scripts.diagnose_credit_e147 import measure,name


class CreditAuditTests(unittest.TestCase):
    def rows(self):
        return [dict(case=str(i),value=r,reward=r,choices=n,entropy=1.,top_probability=1/n,
                     adv=a,raw_adv=b) for i,(r,n,a,b) in enumerate([(-1,1,.2,-.1),(1,2,-.2,-.3)])]

    def test_value_baselines_and_forced_action_accounting(self):
        rows=self.rows();s=measure(rows)
        self.assertEqual(s['explained_variance'],1.);self.assertEqual(s['mse'],0.)
        self.assertEqual(s['forced'],1);self.assertEqual(s['multi'],1)
        self.assertEqual(s['negative_to_positive'],1)
        for r in rows:r['value']=0
        s=measure(rows);self.assertEqual(s['explained_variance'],0.);self.assertEqual(s['r2_vs_return_mean'],0.)

    def test_degenerate_returns_do_not_report_fake_explained_variance(self):
        rows=self.rows()
        for r in rows:r['reward']=-1
        self.assertIsNone(measure(rows)['explained_variance'])
        self.assertEqual(measure([]),{'n':0})

    def test_menu_metadata_may_be_a_list(self):
        action={'action':{'action':'select_cards'},'name':'Choose cards','details':[{'name':'Strike'}]}
        self.assertEqual(name(action),'Choose cards')
        self.assertEqual(name({**action,'details':{'title':'A named option'}}),'A named option')
