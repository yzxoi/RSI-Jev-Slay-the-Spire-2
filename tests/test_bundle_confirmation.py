import unittest

from rsi.scenes import candidates


class BundleConfirmationTests(unittest.TestCase):
    def test_native_post_choice_shape_confirms_without_index(self):
        raw = {'screen': 'BUNDLE_SELECTION', 'run_id': 'EC0JQCUP6QMC',
               'available_actions': ['save_and_quit', 'confirm_bundle'], 'bundles': None,
               'selection': None}
        self.assertEqual(candidates(raw), [{'action': {'action': 'confirm_bundle'},
                                             'name': 'confirm_bundle', 'details': None, 'id': 'a000'}])

    def test_pre_choice_shape_uses_advertised_indices(self):
        raw = {'screen': 'BUNDLE_SELECTION', 'available_actions': ['choose_bundle'],
               'selection': None, 'bundles': [{'index': 3}, {'index': 7}]}
        self.assertEqual([c['action'] for c in candidates(raw)],
                         [{'action': 'choose_bundle', 'option_index': 3},
                          {'action': 'choose_bundle', 'option_index': 7}])

    def test_no_advertised_bundle_action_has_no_candidate(self):
        raw = {'screen': 'BUNDLE_SELECTION', 'available_actions': ['save_and_quit'],
               'selection': None, 'bundles': None}
        self.assertEqual(candidates(raw), [])


if __name__ == '__main__':
    unittest.main()
