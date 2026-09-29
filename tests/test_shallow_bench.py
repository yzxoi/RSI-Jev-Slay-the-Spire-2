import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from rsi.shallow_bench import (CONFIGS, INITIAL_CONFIGS, REPLACEMENT_CONFIGS, digest, make_bank, verify_bank, truth, question,
    request_body, parse_choice, reservation, canonical, solve, rollout)

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('e118_runner',ROOT/'scripts/benchmark_shallow_e118.py')
runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)


class ShallowBenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.bank=make_bank()

    def test_fresh_balanced_bank_and_independent_solver(self):
        report=verify_bank(self.bank)
        self.assertEqual(report['items'],32)
        self.assertEqual(report['calls_per_configuration'],104)
        for item in self.bank['items']:
            w=item['world']; h=item['horizon']
            exhaustive={a:max(rollout(w,[a,*tail])[1] for tail in itertools.product(('A','B'),repeat=h-1)) for a in ('A','B')}
            self.assertEqual(exhaustive,item['root_q'])

    def test_mapping_inversion_changes_only_question_not_world(self):
        for i in self.bank['items']:
            a,b=question(i,'predict_yes_a'),question(i,'predict_yes_b')
            self.assertEqual(a['state'],b['state'])
            self.assertNotEqual(truth(i,'predict_yes_a'),truth(i,'predict_yes_b'))
            self.assertEqual(a['question']['criteria']['A'],b['question']['criteria']['B'])

    def test_identical_semantic_payload_across_model_interfaces(self):
        i=self.bank['items'][0]
        for task in ('choice','predict_yes_a','predict_yes_b','readout'):
            j=request_body('jev',i,task)
            expected={'state':j['state'],'question':j['questions']['answer']}
            for c in CONFIGS:
                if c!='jev':
                    body=request_body(c,i,task)
                    self.assertEqual(json.loads(body['messages'][1]['content']),expected)
                    self.assertFalse(body['provider']['allow_fallbacks'])
                    self.assertEqual(body['max_tokens'],8192)

    def test_strict_output_and_model_provider_validation(self):
        good={'model':CONFIGS['sol_none']['canonical'],'provider':'OpenAI',
              'choices':[{'finish_reason':'stop','message':{'content':'{"choice":"B"}'}}]}
        self.assertEqual(parse_choice('sol_none',good),'B')
        good['choices'][0]['finish_reason']='length'
        with self.assertRaisesRegex(ValueError,'finish_reason_length'): parse_choice('sol_none',good)
        good['provider']='other'
        with self.assertRaisesRegex(ValueError,'unexpected_provider'): parse_choice('sol_none',good)

    def test_ledger_retains_unknown_billing_and_stops_only_its_config(self):
        a,b=runner.Ledger(.5),runner.Ledger(.5)
        self.assertTrue(a.acquire(.1)); a.settle(.1,None,False)
        self.assertEqual(a.unknown_reserved,.1)
        self.assertFalse(a.acquire(.1)); self.assertTrue(b.acquire(.1))
        self.assertAlmostEqual(sum(CONFIGS[c]['cap'] for c in INITIAL_CONFIGS),3.)

    def test_continuation_deduplicates_calls_and_accounts_unknown_spend(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'manifest.json').write_text(json.dumps({'configurations':{'jev':CONFIGS['jev']},'bank_digest':digest(self.bank)}))
            (p/'summary.json').write_text(json.dumps({'total_reported_cost_usd':.006,'total_unknown_reservation_usd':.306}))
            with patch.object(runner,'audit') as audit:
                _,reused,spent,ceiling=runner.continuation_plan(p,self.bank,REPLACEMENT_CONFIGS)
                audit.assert_called_once()
                self.assertEqual(set(reused),{'jev'})
                self.assertAlmostEqual(spent,.312)
                self.assertAlmostEqual(ceiling,2.912)
                with self.assertRaisesRegex(ValueError,'repeat'):
                    runner.continuation_plan(p,self.bank,['jev'])
                with self.assertRaisesRegex(ValueError,'budget'):
                    runner.continuation_plan(p,self.bank,[*REPLACEMENT_CONFIGS,'sol_low'])
        with self.assertRaisesRegex(ValueError,'baseline'):
            runner.continuation_plan(None,self.bank,REPLACEMENT_CONFIGS)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            runner.continuation_plan(None,self.bank,['jev','jev'])

    def test_ledger_deadline_budget_and_failure_exits(self):
        l=runner.Ledger(.1)
        self.assertFalse(l.acquire(.11))
        l=runner.Ledger(.5)
        for _ in range(3):
            self.assertTrue(l.acquire(.1)); l.settle(.1,.001,False)
        self.assertEqual(l.stop,'invalid_response_exit')
        self.assertFalse(l.acquire(.1))

    def test_missing_reasoning_counter_is_not_zero(self):
        self.assertIsNone(runner.reasoning_tokens({}))
        self.assertEqual(runner.reasoning_tokens({'completion_tokens_details':{'reasoning_tokens':0}}),0)
        self.assertEqual(runner.reasoning_tokens({'completion_tokens_details':{'reasoning_tokens':87}}),87)

    def test_total_http_deadline_and_conservative_reservation(self):
        with patch.object(runner.subprocess,'run',side_effect=subprocess.TimeoutExpired('http',60)) as call:
            self.assertEqual(runner.post('sol_low',{},'not-a-real-key'),{'error':'total_http_deadline_60s'})
            self.assertEqual(call.call_args.kwargs['timeout'],60)
            self.assertNotIn('not-a-real-key',str(call.call_args.args))
        for c in CONFIGS:
            body=request_body(c,self.bank['items'][-1],'choice')
            self.assertGreater(reservation(c,body),0)
            self.assertLess(reservation(c,body),CONFIGS[c]['cap'])


if __name__=='__main__': unittest.main()
