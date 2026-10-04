"""E166 opt-in Ashwater polarity correction; no battle or potion-timing changes."""
from .battle_search import CONTROL
from .continuation import FrozenProgram
from .teacher import selection_choice


class TypedAshwaterProgram(FrozenProgram):
    name = 'e166-typed-ashwater-v1'

    def choose(self, state, choices, previous):
        if (state['decision'] == 'card_select' and
                (self.parent or {}).get('details', {}).get('id') == 'ASHWATER'):
            chosen = selection_choice(state, choices,
                {**CONTROL, 'typed_ashwater': True}, self.parent)
            return chosen, dict(program_policy=self.name, route='selection',
                selection_effect='optional_exhaust', selection_parent=self.parent)
        return super().choose(state, choices, previous)
