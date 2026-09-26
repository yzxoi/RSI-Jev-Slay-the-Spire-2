import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from scripts.evaluate_routing_e099 import committed_response

class ExpertPacketCommitTest(unittest.TestCase):
    def test_waits_for_untracked_staged_and_modified_response(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
            git('init');git('config','user.name','Packet Test');git('config','user.email','test@example.invalid')
            git('commit','--allow-empty','-m','baseline')
            path=root/'packet.json';path.write_text(json.dumps({'seq':1})+'\n')
            self.assertIsNone(committed_response(path,root))
            git('add','packet.json');self.assertIsNone(committed_response(path,root))
            git('commit','-m','decision');packet,commit=committed_response(path,root)
            self.assertEqual(packet,{'seq':1});self.assertEqual(commit,git('rev-parse','HEAD'))
            path.write_text(json.dumps({'seq':2})+'\n');self.assertIsNone(committed_response(path,root))
