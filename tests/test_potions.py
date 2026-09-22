import unittest
from rsi.potions import with_potions
class Potions(unittest.TestCase):
 def test_exported_slots_and_targets(self):
  s={'player':{'potions':[{'index':2,'name':'Fire','target_type':'AnyEnemy'},{'index':0,'name':'Block','target_type':'AnyPlayer'}]},'enemies':[{'index':1},{'index':4}]}
  cs=with_potions(s,[])
  self.assertEqual([c['action']['args'] for c in cs],[{'potion_index':2,'target_index':1},{'potion_index':2,'target_index':4},{'potion_index':0}])
