"""Synthetic provenance/transition checks for conservative reset routing."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from rsi.checkpoints import file_hash
from rsi.reset_fallback import recovery_valid,source_plan
from rsi.trace import digest


class ResetFallbackTests(unittest.TestCase):
    def record(self):
        a=dict(status='clear',steps=1,transition_hash='battle',final_hash='terminal')
        b=dict(status='match',path_hash='future',final_hash='next')
        return dict(status='match',native=False,restore_reason='verified_full_prefix_recovery',
                    original_native_failure=dict(status='fail',native=True,A=a,B=b,C1={'status':'error'}),
                    replays=[dict(status='match',mode='A',path_hash='future',final_hash='next') for _ in range(2)]
                            +[{**a,'restore_mode':'full_prefix'}])

    def test_requires_every_full_prefix_replay(self):
        r=self.record()
        self.assertTrue(recovery_valid(r))
        for i in range(3):
            changed=copy.deepcopy(r)
            changed['replays'][i]['final_hash']='wrong'
            self.assertFalse(recovery_valid(changed))
        r['replays'].pop()
        self.assertFalse(recovery_valid(r))

    def test_native_mode_cannot_be_smuggled_into_fallback(self):
        r=self.record();r['replays'][2]['restore_mode']='research_checkpoint'
        self.assertFalse(recovery_valid(r))
        r=self.record();r['snapshot']={'path':'bad'}
        self.assertFalse(recovery_valid(r))

    def test_only_native_incompatibility_is_eligible(self):
        r=self.record();r['original_native_failure']['A']['status']='timeout'
        self.assertFalse(recovery_valid(r))
        r=self.record();r['original_native_failure']['B']['status']='error'
        self.assertFalse(recovery_valid(r))

    def test_save_protocol_removed_but_game_actions_and_hashes_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            trace=Path(directory)/'decisions.jsonl';trace.write_text('{}\n')
            wire=trace.with_name('wire.jsonl')
            start={'cmd':'start_run'};enter={'cmd':'action','action':'select_map_node'}
            end={'cmd':'action','action':'end_turn'}
            m={'decision':'map_select'};c={'decision':'combat_play'};t={'decision':'game_over'}
            pairs=[(start,m),({'cmd':'write_continue_save'},{'success':True}),(enter,c),(end,t)]
            rows=[]
            for cmd,state in pairs:rows.extend([{'kind':'command','data':cmd},{'kind':'state','data':state}])
            wire.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            steps=[{'before':digest(c),'action':end,'after':digest(t)}]
            f={'prefix':[start,enter],'entry_hash':digest(c)}
            r={'trace_path':str(trace),'trace_sha256':file_hash(trace),'wire.jsonl_sha256':file_hash(wire),
               'path_hash':digest(steps),'final_hash':digest(t)}
            self.assertEqual(source_plan(f,r,continuation=True),steps)
            r['path_hash']='wrong'
            with self.assertRaisesRegex(ValueError,'path/final'):
                source_plan(f,r,continuation=True)


if __name__=='__main__':unittest.main()
