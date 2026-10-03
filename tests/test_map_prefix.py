"""Synthetic restore-contract checks, not game mechanic or win-rate evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rsi.checkpoints import file_hash
from rsi.map_prefix import identity, restore
from rsi.research_restore import ENGINE_KEYS
from rsi.trace import digest


class MapPrefixTests(unittest.TestCase):
    def fixture(self, directory):
        states=[dict(decision='map_select',context={'room_type':'Map'}),dict(decision='card_reward',cards=[])]
        commands=[dict(cmd='start_run'),dict(cmd='action',action='example')]
        root=dict(case='synthetic',prefix=commands,prefix_hash=digest(commands),root_hash=digest(states[-1]),
            prefix_state_hashes=[digest(s) for s in states],seed='synthetic',ascension=5)
        file=directory/'save.json';file.write_text(json.dumps(dict(ascension=5,rng={'seed':'synthetic'})))
        manifest={k:'fixed' for k in ENGINE_KEYS}
        snap={k:root[k] for k in ('case','prefix_hash','root_hash')} | dict(path='save.json',sha256=file_hash(file),
            engine=manifest,map_offset=0,map_hash=digest(states[0]))
        return root,snap,manifest,states

    def test_native_identity_and_bytes_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as folder, patch('rsi.map_prefix.ROOT',Path(folder)):
            root,snap,manifest,_=self.fixture(Path(folder))
            identity(root,snap,manifest)
            with self.assertRaises(ValueError):identity({**root,'ascension':10},snap,manifest)
            with self.assertRaises(ValueError):identity({**root,'root_hash':'another'},snap,manifest)
            with self.assertRaises(ValueError):identity(root,snap,{**manifest,ENGINE_KEYS[0]:'new-runtime'})
            (Path(folder)/'save.json').write_text('{}')
            with self.assertRaises(ValueError):identity(root,snap,manifest)

    def test_short_prefix_checks_map_and_every_later_response(self):
        with tempfile.TemporaryDirectory() as folder, patch('rsi.map_prefix.ROOT',Path(folder)):
            root,snap,manifest,states=self.fixture(Path(folder))
            responses=iter(states);sent=[]
            def send(c):sent.append(c);return next(responses)
            final,n=restore(send,root,manifest,Path(folder),snapshot=snap)
            self.assertEqual(final,states[-1]);self.assertEqual(n,2)
            self.assertEqual(sent[0]['cmd'],'load_save');self.assertEqual(sent[1],root['prefix'][1])
            responses=iter([states[0],dict(decision='unexpected')])
            with self.assertRaises(ValueError):restore(send,root,manifest,Path(folder),snapshot=snap)


if __name__=='__main__':unittest.main()
