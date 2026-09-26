import unittest
from rsi.room_owner import RoomOwner, bind_selector
from rsi.trace import digest
from rsi.policy import combat_candidates

class RoomOwnerTest(unittest.TestCase):
    def state(self, index=0):
        return {'context':{'floor':17}, 'decision':'combat_play', 'round':1, 'hand':[
            {'index':index,'id':'CARD.X','name':'X','can_play':True,'target_type':'AnyEnemy'}],
            'enemies':[{'index':2,'name':'Boss'}], 'draw_pile_count':9}
    def test_rebinds_fresh_hand_index(self):
        state=self.state(4)
        choice=bind_selector({'card':'X','enemy':'Boss'}, state, combat_candidates(state))
        self.assertEqual(choice['action']['args'],{'card_index':4,'target_index':2})
    def test_stale_packet_and_id_batch_rejected(self):
        s=self.state();o=RoomOwner(s,'astra')
        with self.assertRaises(ValueError):o.accept({'state_hash':'stale'},s)
        with self.assertRaises(ValueError):o.accept({'state_hash':digest(s),'reason':'x','actions':[{'choice':'a000'},{'end_turn':True}]},s)
    def test_draw_and_selection_clear_queue_preserve_owner(self):
        s=self.state();o=RoomOwner(s,'astra')
        p={'state_hash':digest(s),'reason':'known current hand','actions':[{'end_turn':True}]}
        for after in [{**s,'draw_pile_count':8},{**s,'decision':'card_select'},{**s,'round':2}]:
            o.accept(p,s);o.observed(s,after);self.assertEqual(o.queue,[]);self.assertEqual(o.mode,'astra')
    def test_room_expiry(self):
        s=self.state();o=RoomOwner(s,'astra')
        with self.assertRaises(ValueError):o.next({**s,'context':{'floor':18}},[])
