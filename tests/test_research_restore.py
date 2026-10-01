import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rsi.battle_search import same_trajectory
from rsi.checkpoints import file_hash
from rsi.research_restore import research_snapshots, restore_entry


class ResearchRestoreTests(unittest.TestCase):
    def test_unpromoted_snapshot_is_not_enabled_implicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'index.json'
            p.write_text(json.dumps({'fidelity_pass':True,'performance_promotion_pass':False}))
            with self.assertRaisesRegex(ValueError,'opt-in'):
                research_snapshots(p, {})

    def test_same_final_outcome_does_not_hide_a_transition_difference(self):
        r=dict(status='clear',path_hash='actions',transition_hash='path1',final_hash='end',steps=3)
        self.assertFalse(same_trajectory(r,{**r,'transition_hash':'path2'}))
        self.assertTrue(same_trajectory(r,dict(r)))

    def test_wrong_history_is_rejected_before_engine_call(self):
        snapshot={'allow_unpromoted':True,'case':'other','prefix_hash':'x'}
        with patch('builtins.print'):
            def send(_):
                self.fail('No engine action allowed')
            with self.assertRaisesRegex(ValueError,'history'):
                restore_entry(send,{'case':'this'},snapshot,{})

    def test_edited_snapshot_is_rejected_before_engine_call(self):
        from rsi.trace import digest
        from rsi.research_restore import ENGINE_KEYS
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'checkpoint.json';p.write_text('{}')
            manifest={k:'pinned' for k in ENGINE_KEYS}
            frozen={'case':'c','prefix':[],'entry_hash':'entry'}
            snapshot={'allow_unpromoted':True,'case':'c','prefix_hash':digest([]),'entry_hash':'entry',
                      'engine':manifest,'path':str(p),'sha256':file_hash(p)}
            p.write_text('{"hp":999}')
            def send(_):
                self.fail('No engine action allowed')
            with self.assertRaisesRegex(ValueError,'bytes changed'):
                restore_entry(send,frozen,snapshot,manifest)


if __name__=='__main__':
    unittest.main()
