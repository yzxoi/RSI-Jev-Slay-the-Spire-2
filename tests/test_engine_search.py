"""Synthetic boundary/certificate checks; these are not game wins."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from rsi.engine import action
from rsi.engine_search import (EngineSearch, LIMITS, POLICIES, combat_boundary, fresh_choices,
                              macro_choice, needs_refresh, outcome_rank, prefix_digest, probe)
from rsi.trace import digest


class Sink:
    def write(self, *args):
        pass


def state():
    return dict(decision='combat_play', round=1, context={'act': 1, 'floor': 1}, energy=1,
                player={'hp': 20, 'max_hp': 20, 'block': 0, 'potions': [], 'potion_capacity': 3},
                enemies=[dict(index=7, hp=20, intents=[], powers=[])],
                hand=[dict(index=4, id='CARD.STRIKE', name='Strike', can_play=True, cost=1,
                           type='Attack', target_type='AnyEnemy', stats={'damage': 6},
                           damage_by_target=[{'target_index': 7, 'damage': 6}])])


class EngineSearchTests(unittest.TestCase):
    def test_reward_boundaries(self):
        self.assertIsNone(combat_boundary(dict(decision='card_reward', from_event=True)))
        self.assertEqual(combat_boundary(dict(decision='potion_reward', player={'hp': 5})), 'clear')
        self.assertEqual(combat_boundary(dict(decision='game_over', player={'hp': 0})), 'defeat')
        with self.assertRaises(RuntimeError):
            combat_boundary(dict(decision='card_reward', player={'hp': 20}))

    def test_inventory_claim_and_full_skip(self):
        s = dict(decision='potion_reward', can_claim=True, can_skip=True,
                 potion={'id': 'POTION.BLOCK'}, player={'potions': [], 'has_open_potion_slots': True})
        self.assertEqual(macro_choice(s)['action']['action'], 'claim_potion_reward')
        s.update(can_claim=False)
        s['player'].update(has_open_potion_slots=False,
                           potions=[dict(index=2, name='Block Potion', can_use=False, can_discard=True)])
        self.assertEqual(macro_choice(s)['action']['action'], 'skip_potion_reward')

    def test_cache_requires_full_history_and_observation(self):
        s = state()
        planner = EngineSearch({}, Sink())
        result = dict(status='clear', mode='control')
        key = prefix_digest([{'cmd': 'start_run', 'seed': 'a'}])
        record = dict(prefix_hash=key, before=digest(s), action=action('end_turn'),
                      after='next', source_trace='synthetic', mode='control')
        planner.remember(result, [record])
        self.assertIsNotNone(planner.lookup('control', key, s))
        self.assertIsNone(planner.lookup('control', prefix_digest([{'cmd': 'start_run', 'seed': 'b'}]), s))
        self.assertIsNone(planner.lookup('control', key, {**s, 'energy': 2}))
        planner.remember(dict(status='timeout', mode='defend'), [record])
        self.assertIsNone(planner.lookup('defend', key, s))

    def test_actual_transition_mismatch_stops(self):
        s = state()
        planner = EngineSearch({}, Sink())
        with self.assertRaisesRegex(ValueError, 'differs'):
            planner.observe(s, fresh_choices(s)[0], s, {'after': 'wrong'})
        self.assertEqual(planner.stats['prediction_mismatches'], 1)
        self.assertTrue(planner.refresh)
        self.assertFalse(planner.cache)

    def test_draw_same_id_and_selection_refresh(self):
        s = state()
        c = fresh_choices(s)[0]
        self.assertFalse(needs_refresh(s, c, {**s, 'hand': []}))
        self.assertTrue(needs_refresh(s, c, s))  # Played Strike, drew another Strike.
        self.assertTrue(needs_refresh(s, c, {**s, 'round': 2}))
        self.assertTrue(needs_refresh(s, c, {'decision': 'card_select'}))

    def test_incomplete_rollouts_never_rank_as_wins(self):
        win = dict(status='clear', hp=1, potions_left=0, round=10)
        loss = dict(status='defeat', hp=0, enemy_hp=0, round=2)
        self.assertGreater(outcome_rank(win), outcome_rank(loss))
        for status in ('error', 'timeout', 'action_cap'):
            with self.assertRaises(ValueError):
                outcome_rank({**win, 'status': status})

    def test_budget_falls_back_to_control_without_probe(self):
        planner = EngineSearch({}, Sink(), {**LIMITS, 'batches': 0})
        s = state()
        proposals = [fresh_choices(s)[0], fresh_choices(s)[-1]]
        with patch('rsi.engine_search.select', side_effect=[(proposals[i % 2], [], {})
                                                           for i in range(len(POLICIES))]), \
             patch('rsi.engine_search.probe') as branch:
            choice, proof, reason = planner.decide(s, [], prefix_digest([]), None, time.monotonic() + 30)
        self.assertEqual(choice, proposals[0])
        self.assertIsNone(proof)
        self.assertEqual(reason, 'budget_control')
        branch.assert_not_called()

    def test_probe_rejects_wrong_replay_before_action(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('rsi.engine_search.ROOT', Path(tmp)), \
             patch('rsi.engine_search.Headless') as engine:
            engine.return_value.send.return_value = {'decision': 'combat_play', 'wrong': True}
            def close():
                for path in Path(tmp).glob('artifacts/runs/*'):
                    (path / 'engine.stderr.log').write_text('')
            engine.return_value.close.side_effect = close
            result, path = probe([{'cmd': 'start_run'}], state(), None, 'control', {}, LIMITS, 5)
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['entry_verified'])
        self.assertEqual(result['error'], 'ValueError: Replay entry mismatch')
        self.assertEqual(engine.return_value.send.call_count, 1)
        self.assertFalse(path)


if __name__ == '__main__':
    unittest.main()
