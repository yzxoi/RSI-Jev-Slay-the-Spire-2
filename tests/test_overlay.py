import unittest

from rsi.overlay import display_options


class OverlayTests(unittest.TestCase):
    def test_long_choice_list_keeps_actual_selection(self):
        options = [{"label": str(i), "probability": i / 10, "selected": i == 8} for i in range(9)]
        shown, hidden = display_options({"options": options, "option_count": 9}, limit=5)
        self.assertEqual(len(shown), 5)
        self.assertTrue(shown[-1]["selected"])
        self.assertEqual(hidden, 4)

    def test_missing_distribution_stays_missing(self):
        shown, hidden = display_options({"options": [{"label": "Astra", "probability": None, "selected": True}]})
        self.assertIsNone(shown[0]["probability"])
        self.assertEqual(hidden, 0)


if __name__ == "__main__":
    unittest.main()
