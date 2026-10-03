"""Frozen program continuation and observational first-fight measurement for E159."""
from .curriculum import FightBoundary, cautious_macro, ROOMS
from .ppo_actions import complete_baseline
from .root_teacher import utility
from .trace import digest


def interruption(state):
    return state['decision'] == 'card_select' or (
        state['decision'] == 'card_reward' and state.get('from_event') and
        (state.get('context') or {}).get('room_type') in ROOMS)


class FrozenProgram:
    name = 'e159-legacy-early-potions-cautious-campaign-v1'

    def __init__(self, previous):
        self.parent = previous
        self.origin = 'source_previous'

    def choose(self, state, choices, previous):
        selection = interruption(state)
        combat = state['decision'] == 'combat_play'
        if combat or selection:
            selected = complete_baseline(state, choices, self.parent if selection else previous)
        else:
            selected = cautious_macro(state)
        return selected, dict(program_policy=self.name,
            route='selection' if selection else 'combat' if combat else 'campaign',
            selection_origin=self.origin if selection else None,
            selection_parent=self.parent if selection else None)

    def remember(self, state, chosen):
        # Preserve the triggering card/potion across a chain of selection menus.
        if not interruption(state):
            self.parent, self.origin = chosen, state['decision']


class FirstFight:
    """Record a genuine first encounter once; keep playing to actual game-over."""
    def __init__(self):
        self.tracker = FightBoundary()
        self.result = None

    @staticmethod
    def resources(state):
        p = state.get('player') or {}
        return dict(hp=p.get('hp', 0), max_hp=p.get('max_hp', 1), gold=p.get('gold', 0),
            potions=[x.get('id', x.get('name')) for x in p.get('potions', [])],
            deck_hash=digest(p.get('deck')))

    def observe(self, state, plan):
        if self.result is not None:
            return
        outcome = self.tracker.observe(state)
        if outcome is None:
            return
        if outcome == 'clear' and not self.tracker.started:
            raise ValueError('Unplayed first encounter cannot be a clear')
        self.result = dict(status=outcome, steps=len(plan), **self.resources(state),
            started=self.tracker.started, room_type=self.tracker.room_type, act=self.tracker.act,
            final_hash=digest(state), transition_hash=digest(plan))
        self.result['utility'] = utility(self.result)
