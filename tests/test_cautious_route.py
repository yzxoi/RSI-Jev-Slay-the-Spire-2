import unittest

from rsi.full import fixed_macro


def map_state(hp, max_hp=80):
    return {'decision': 'map_select', 'player': {'hp': hp, 'max_hp': max_hp, 'gold': 0}}


def candidate(kind, index):
    return {'id': str(index), 'action': {'cmd': 'action', 'action': 'select_map_node',
                                        'args': {'col': index, 'row': 1}}, 'details': {'type': kind}}


class CautiousRouteTests(unittest.TestCase):
    def test_low_hp_unknown_beats_monster_only_in_treatment(self):
        choices = [candidate('Monster', 0), candidate('Unknown', 1)]
        self.assertEqual(fixed_macro(map_state(36), choices)['id'], '0')
        self.assertEqual(fixed_macro(map_state(36), choices, cautious_route=True)['id'], '1')
        self.assertEqual(fixed_macro(map_state(37), choices, cautious_route=True)['id'], '0')

    def test_better_routes_keep_priority(self):
        choices = [candidate('Monster', 0), candidate('Unknown', 1), candidate('RestSite', 2)]
        self.assertEqual(fixed_macro(map_state(20), choices, cautious_route=True)['id'], '2')
        choices.append(candidate('Treasure', 3))
        self.assertEqual(fixed_macro(map_state(20), choices, cautious_route=True)['id'], '3')


if __name__ == '__main__':
    unittest.main()
