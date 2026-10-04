"""Factorial E168 policy: independent applicability and selection-polarity switches."""
from .battle_search import CONTROL
from .continuation import FrozenProgram
from .selection_semantics import TypedAshwaterProgram
from .teacher import select


class PotionProgram(TypedAshwaterProgram):
    def __init__(self,previous,applicability=False,typed_ashwater=False):
        super().__init__(previous)
        self.applicability=applicability;self.typed_ashwater=typed_ashwater
        self.name=f'e168-applicability-{int(applicability)}-typed-{int(typed_ashwater)}'

    def choose(self,state,choices,previous):
        if self.applicability and state['decision']=='combat_play':
            chosen,_,meta=select(state,{**CONTROL,'potion_applicability':True},previous)
            return chosen,dict(program_policy=self.name,route='combat',**meta)
        if self.typed_ashwater:return super().choose(state,choices,previous)
        return FrozenProgram.choose(self,state,choices,previous)
