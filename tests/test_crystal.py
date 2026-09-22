import copy
import unittest
from rsi.scenes import candidates,fingerprint

class CrystalTests(unittest.TestCase):
    def board(self):
        return {'screen':'CRYSTAL_SPHERE','available_actions':['crystal_clear_cell','crystal_set_tool'], 'crystal_sphere':{'divinations_left':3,'is_finished':False,'hidden_cells':[[1,2],[3,4]]}}
    def test_atomic_coordinates_and_tools(self):
        actions=[c['action'] for c in candidates(self.board())]
        self.assertEqual(actions,[{'action':'crystal_clear_cell','x':x,'y':y,'tool':t} for x,y in [(1,2),(3,4)] for t in ['big','small']])
    def test_finished_requires_advertised_proceed(self):
        s=self.board();s['crystal_sphere']['is_finished']=True
        self.assertEqual(candidates(s),[])
        s['available_actions']=['proceed']
        self.assertEqual(candidates(s)[0]['action'],{'action':'proceed'})
    def test_no_invented_cells_or_actions(self):
        s=self.board();s['crystal_sphere']['hidden_cells']=[]
        self.assertEqual(candidates(s),[])
        s=self.board();s['available_actions']=[]
        self.assertEqual(candidates(s),[])
    def test_board_mutation_invalidates_expert_choice(self):
        s=self.board();t=copy.deepcopy(s);t['crystal_sphere']['hidden_cells'].pop()
        self.assertNotEqual(fingerprint(s),fingerprint(t))
