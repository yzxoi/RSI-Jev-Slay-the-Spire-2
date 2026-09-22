import copy
import unittest
from rsi.settle import settle_turn

class Fake:
    def __init__(self, states): self.states=iter(states); self.now=0.; self.events=[];self.calls=[]
    def call(self, name):
        self.calls.append(name)
        self.last=next(self.states,self.last if hasattr(self,'last') else None)
        return copy.deepcopy(self.last)
    def write(self,k,d):self.events.append((k,d))
    def clock(self):return self.now
    def sleep(self,dt):self.now+=dt
    def run(self,first):return settle_turn(self,first,self,clock=self.clock,sleep=self.sleep)

def state(cards=5,ready=True):
    return {'run_id':'test','screen':'COMBAT','turn':2,'run':{'floor':5},'available_actions':['play_card','end_turn'],'combat':{'hand':list(range(cards)),'action_readiness':{'can_use_combat_actions':ready}}}

class SettleTests(unittest.TestCase):
    def test_ready_partial_hand_must_reach_quiet_complete_state(self):
        f=Fake([state(2),state(3),state(5)])
        self.assertEqual(len(f.run(state(1))['combat']['hand']),5)
        self.assertGreaterEqual(f.now,1.05)
        self.assertEqual(set(f.calls),{'get_raw_game_state'})
    def test_unready_timeout_never_sends_action(self):
        f=Fake([state(5,False)])
        with self.assertRaises(TimeoutError):f.run(state(5,False))
        self.assertEqual(set(f.calls),{'get_raw_game_state'})
    def test_run_change_stops(self):
        other=state();other['run_id']='other';f=Fake([other])
        with self.assertRaises(RuntimeError):f.run(state())
    def test_card_selection_returns_for_fresh_routing(self):
        modal=state();modal['screen']='CARD_SELECTION';modal['selection']={'cards':[]};f=Fake([modal])
        self.assertEqual(f.run(state())['screen'],'CARD_SELECTION')
    def test_end_turn_legal_set_is_part_of_stability(self):
        s=state();s['available_actions']=['end_turn'];f=Fake([s])
        self.assertEqual(f.run(state())['available_actions'],['end_turn'])
        self.assertGreaterEqual(f.now,.75)
