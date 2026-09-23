import copy
import unittest

from rsi.deck_context import deck_advice, deck_profile


class DeckContextTests(unittest.TestCase):
    def test_printed_coverage_and_starters(self):
        state = {'player': {'deck': [
            {'id': 'CARD.STRIKE_IRONCLAD', 'type': 'Attack', 'stats': {'damage': 6}},
            {'id': 'CARD.DEFEND_IRONCLAD', 'type': 'Skill', 'stats': {'block': 5}},
            {'id': 'CARD.BATTLE_TRANCE', 'type': 'Skill', 'stats': {'cards': 3}},
            {'id': 'CARD.PYRE', 'type': 'Power', 'stats': {'energy': 1}},
        ]}}
        original = copy.deepcopy(state)
        self.assertEqual(deck_profile(state), {
            'deck_size': 4, 'attacks': 1, 'skills': 2, 'powers': 1,
            'printed_block_cards': 1, 'printed_draw_cards': 1,
            'printed_energy_cards': 1, 'starter_strikes': 1,
            'starter_defends': 1, 'attack_heavy': False})
        self.assertEqual(state, original)

    def test_missing_fields_are_zero_coverage(self):
        self.assertEqual(deck_profile({})['deck_size'], 0)
        profile = deck_profile({'player': {'deck': [{}, {'type': 'Attack', 'stats': None}]}})
        self.assertEqual((profile['attacks'], profile['printed_block_cards'],
                          profile['printed_draw_cards']), (1, 0, 0))

    def test_attack_heavy_advice_is_conditional(self):
        state = {'player': {'deck': ([{'type': 'Attack'}] * 10 +
                                     [{'type': 'Skill', 'stats': {'block': 5}}] * 3 +
                                     [{'type': 'Skill', 'stats': {'cards': 2}}] * 2)}}
        profile = deck_profile(state)
        self.assertTrue(profile['attack_heavy'])
        self.assertIn('reliable block or draw', deck_advice(profile))
        self.assertNotIn('Attack-heavy', deck_advice(deck_profile({})))


if __name__ == '__main__':
    unittest.main()
