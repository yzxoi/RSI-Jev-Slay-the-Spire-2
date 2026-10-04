"""Small frozen battle-policy family for real-engine objective selection experiments."""
from .battle_search import CONTROL
from .continuation import FrozenProgram
from .teacher import select

OBJECTIVES=('baseline','leader','setup','leader_setup')


class ObjectiveProgram(FrozenProgram):
    def __init__(self,previous,objective):
        if objective not in OBJECTIVES:raise ValueError('Unknown objective')
        super().__init__(previous);self.objective=objective

    def choose(self,state,choices,previous):
        if state['decision']!='combat_play' or self.objective=='baseline':
            return super().choose(state,choices,previous)
        chosen,_,planning=select(state,{**CONTROL,'objective':self.objective},previous)
        return chosen,dict(objective=self.objective,planning=planning)
