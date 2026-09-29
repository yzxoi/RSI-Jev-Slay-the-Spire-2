import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('minimal_bench_runner', ROOT/'scripts/benchmark_minimal_e116.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def simulated_run(self, reply):
        raw_root = ROOT/'artifacts/runs'; raw_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=raw_root) as directory:
            directory = Path(directory)
            bank_path = directory/'bank.json'
            runner.write_json(bank_path, runner.make_bank())
            args = argparse.Namespace(execute=True, bank=str(bank_path), output=str(directory/'out'), env_file='unused')
            git = lambda argv, **kwargs: '' if argv[1] == 'status' else 'synthetic-test-sha'
            with patch.object(runner, 'read_key', return_value='not-a-real-credential'), \
                 patch.object(runner, 'post', return_value=reply) as post, \
                 patch.object(runner.subprocess, 'check_output', side_effect=git), \
                 patch.object(runner.subprocess, 'check_call'), \
                 patch.object(runner, 'summarize', return_value={}), \
                 contextlib.redirect_stdout(io.StringIO()):
                runner.run(args)
            return (post.call_count,
                    json.loads((directory/'out/rows.json').read_text()),
                    json.loads((directory/'out/manifest.json').read_text()))

    def test_unknown_billing_stops_without_retry_and_retains_all_cells(self):
        count, rows, manifest = self.simulated_run({'error': 'simulated timeout'})
        self.assertEqual(count, 1)
        self.assertEqual(len(rows), 216)
        self.assertEqual(sum(r['attempted'] for r in rows), 1)
        self.assertEqual(sum(r['correct'] for r in rows), 0)
        self.assertEqual(manifest['stop_reason'], 'unknown_billing')

    def test_three_invalid_responses_are_billed_and_stop(self):
        reply = {'response': {'model': runner.MODEL, 'provider': 'TypeSafe',
                              'answers': {}, 'usage': {'cost': .0001}}}
        count, rows, manifest = self.simulated_run(reply)
        self.assertEqual(count, 3)
        self.assertEqual(sum(r['valid'] for r in rows), 0)
        self.assertAlmostEqual(manifest['billed_cost_usd'], .0003)
        self.assertEqual(manifest['stop_reason'], 'three_consecutive_invalid_responses')

    def test_unexpected_single_call_cost_stops(self):
        reply = {'response': {'model': runner.MODEL, 'provider': 'TypeSafe',
            'answers': {'answer': {'choice': 'A'}}, 'usage': {'cost': .006}}}
        count, rows, manifest = self.simulated_run(reply)
        self.assertEqual(count, 1)
        self.assertEqual(manifest['stop_reason'], 'cost_exceeded_reservation')

    def test_total_deadline_is_not_a_socket_inactivity_timeout(self):
        with patch.object(runner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('worker', 25)) as call:
            self.assertEqual(runner.post({}, 'not-a-real-credential'), {'error': 'total_http_deadline_25s'})
            self.assertEqual(call.call_args.kwargs['timeout'], 25)
            self.assertNotIn('not-a-real-credential', str(call.call_args.args))

    def test_wrong_model_and_provider_are_not_silently_accepted(self):
        self.assertEqual(runner.validate_response({'model': None}), 'unexpected_model')
        self.assertEqual(runner.validate_response({'model': runner.MODEL, 'provider': 'other'}), 'unexpected_provider')


if __name__ == '__main__':
    unittest.main()
