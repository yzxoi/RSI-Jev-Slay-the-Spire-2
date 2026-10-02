"""Synthetic reset/split/selection checks; no playing-strength evidence."""
import unittest
from unittest.mock import patch

from rsi.ppo_env import episode
from rsi.trace import digest
from scripts.retrain_ppo_e133 import CONFIGS, training_pool, training_entries, panel_entries, selection_score


class BankTests(unittest.TestCase):
    def test_distinct_seeds_and_balanced_ascensions(self):
        self.assertEqual(len({c['seed'] for c in CONFIGS}), 264)
        for split,n in [('train',192),('val',24),('test',48)]:
            rows=[c for c in CONFIGS if c['split']==split]
            for asc in (0,5,10):
                self.assertEqual(sum(c['ascension']==asc for c in rows),n//3)

    def test_entry_sampling_has_no_outcome_filter(self):
        fs=[dict(case=f'c{i}',seed_index=0,hp=1 if i==4 else 80) for i in range(5)]
        self.assertEqual([f['case'] for f in training_pool(fs)],['c0','c1','c4'])
        b={'seeds':[{'split':'train','entries':fs}]}
        self.assertEqual([training_entries(b,i)[0]['case'] for i in range(1,7)],['c0','c1','c4']*2)
        self.assertEqual(training_pool(fs[:1]),fs[:1])

    def test_duplicate_panel_identity_remains_visible(self):
        f={'case':'same'}
        self.assertEqual(panel_entries({'seeds':[{'split':'test','entries':[f]}]},'test'),
                         [('early',f),('challenging',f)])

    def test_selection_prefers_challenging_clears_and_earliest_tie(self):
        def v(c,r,e,i):
            return dict(update=i,panels={'challenging':dict(clears=c,mean_reward=r),
                                        'early':dict(clears=e,mean_reward=1.)})
        self.assertGreater(selection_score(v(5,0.,1,8)),selection_score(v(4,1.,24,32)))
        self.assertGreater(selection_score(v(5,1.,24,8)),selection_score(v(5,1.,24,32)))

    def test_checkpoint_episode_skips_whole_game_prefix(self):
        state={'decision':'game_over','victory':False,'player':{'hp':0,'max_hp':80}}
        prefix=[{'cmd':'start_run','seed':'synthetic'}]
        f=dict(case='synthetic',prefix=prefix,prefix_hash=digest(prefix),entry_hash=digest(state),previous=None)
        with patch('rsi.ppo_env.Trace'), patch('rsi.ppo_env.Headless') as engine, \
             patch('rsi.ppo_env.finish'), patch('rsi.research_restore.restore_entry',return_value=state) as restore:
            r,_=episode(f,{},'synthetic',checkpoint={'case':'synthetic'})
        restore.assert_called_once()
        engine.return_value.send.assert_not_called()
        self.assertEqual(r['restore_mode'],'research_checkpoint')
        self.assertEqual(r['status'],'defeat')

    def test_reset_rejection_is_not_a_defeat_reward(self):
        prefix=[{'cmd':'start_run'}]
        f=dict(case='synthetic',prefix=prefix,prefix_hash=digest(prefix),entry_hash='unused',previous=None)
        with patch('rsi.ppo_env.Trace'), patch('rsi.ppo_env.Headless') as engine, \
             patch('rsi.ppo_env.finish'), patch('rsi.research_restore.restore_entry',side_effect=ValueError('Edited snapshot')):
            r,_=episode(f,{},'synthetic',checkpoint={'case':'synthetic'})
        engine.return_value.send.assert_not_called()
        self.assertEqual(r['status'],'error')
        self.assertNotIn('reward',r)


if __name__=='__main__':
    unittest.main()
