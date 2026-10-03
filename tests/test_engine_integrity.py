"""Synthetic stderr-integrity checks, not win-rate evidence."""
import tempfile
import time
import unittest
from pathlib import Path
from rsi.battle_search import finish
from rsi.trace import Trace

class IntegrityTests(unittest.TestCase):
    def test_async_failure_invalidates_apparent_victory(self):
        from rsi.engine import ROOT
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts/runs') as tmp:
            trace=Trace(Path(tmp), {'synthetic':True})
            (Path(tmp)/'engine.stderr.log').write_text('System.MissingMethodException: Missing ABI')
            result={'status':'victory'}
            finish(trace,result,None,time.monotonic())
            self.assertEqual(result['status'],'error')
            self.assertIn('MissingMethodException',result['error'])
