import unittest
from rsi.progress import progress,compare
class ProgressTests(unittest.TestCase):
    def test_cross_act(self):
        self.assertGreater(progress({'act':2,'floor':6}),progress({'act':1,'floor':17}))
        self.assertGreater(progress({'status':'victory','act':3,'floor':16}),progress({'act':3,'floor':17}))
    def test_failures_not_omitted_or_ranked(self):
        common={'character':'Ironclad','seed':'s','ascension':10}
        r=[dict(common,policy='a',status='normal_defeat',act=1,floor=17),dict(common,policy='b',status='error',act=2,floor=6)]
        self.assertEqual(compare(r,'a','b')['outcomes'],{'incomplete_or_error':1})
        r[1]['status']='normal_defeat';self.assertEqual(compare(r,'a','b')['outcomes'],{'better':1})
