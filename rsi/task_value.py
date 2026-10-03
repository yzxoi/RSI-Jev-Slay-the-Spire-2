"""E148 isolated critic probes; never updates or supplies actions to an actor."""
import copy
import numpy as np
import torch
from torch import nn
from .battle_search import boundary
from .phase_rl import STATE_SIZE

PHASES=('combat_play','card_select','event_choice','map_select','card_reward',
        'potion_reward','rest_site','shop','bundle_select')
TASK_DIM=5


class Progress:
    def __init__(self,ascension,target=6):
        self.ascension,self.target=ascension,target
        self.active=False;self.completed=0

    def observe(self,state):
        if self.active:
            outcome=boundary(state)
            if outcome:
                self.active=False;self.completed+=int(outcome=='clear')
        if state['decision']=='combat_play':self.active=True
        if not 0<=self.completed<=self.target:raise ValueError('Invalid observed task progress')
        return dict(goal='six_battles',target=self.target,completed=self.completed,
                    remaining=self.target-self.completed,ascension=self.ascension)


def task_features(context):
    if context['goal']!='six_battles' or context['target']!=6:raise ValueError('Unregistered goal')
    if context['remaining']!=6-context['completed']:raise ValueError('Inconsistent task context')
    return np.asarray([1.,.6,context['completed']/6,context['remaining']/6,context['ascension']/10],dtype=np.float32)


class Critic(nn.Module):
    def __init__(self,actor):
        super().__init__()
        self.state=copy.deepcopy(actor.state)
        first=self.state[0]
        self.state[0]=nn.Linear(STATE_SIZE+TASK_DIM,first.out_features)
        with torch.no_grad():
            self.state[0].weight.zero_();self.state[0].weight[:,:STATE_SIZE].copy_(first.weight)
            self.state[0].bias.copy_(first.bias)
        self.value=copy.deepcopy(actor.value)
        with torch.no_grad():self.value.weight.zero_();self.value.bias.zero_()

    def forward(self,x):return self.value(self.state(x)).squeeze(-1)


def balanced_weights(case_ids):
    _,inverse,counts=np.unique(case_ids,return_inverse=True,return_counts=True)
    return (len(case_ids)/(len(counts)*counts[inverse])).astype(np.float32)


def metrics(prediction,target,case_ids):
    if not len(target):return {'n':0,'trajectories':0}
    p=np.asarray(prediction,dtype=np.float64);y=np.asarray(target,dtype=np.float64)
    if not np.isfinite(p).all() or not np.isfinite(y).all():raise ValueError('Nonfinite value data')
    w=balanced_weights(case_ids).astype(np.float64);w/=w.sum()
    err=p-y;bias=float(w@err);mse=float(w@(err**2));var=float(w@((y-w@y)**2))
    return dict(n=len(y),trajectories=len(np.unique(case_ids)),mse=mse,rmse=mse**.5,
        mae=float(w@abs(err)),bias=bias,mean_value=float(w@p),mean_return=float(w@y),
        return_variance=var,ev=1-float(w@((err-bias)**2))/var if var>1e-12 else None,
        r2=1-mse/var if var>1e-12 else None)


def ridge_features(states,tasks,phases):
    """Explicit phase/progress/HP baseline, with no outcome-derived inputs."""
    count=np.rint(tasks[:,2]*6).astype(int);asc=np.rint(tasks[:,4]*10).astype(int)
    phase=np.eye(len(PHASES))[phases];hp=states[:,0:1].astype(np.float64)
    goal=(count==6).astype(float)[:,None]
    return np.concatenate([np.ones((len(states),1)),np.eye(7)[count],
        np.stack([asc==a for a in (0,5,10)],axis=1),phase,hp,
        goal,goal*hp,phase*tasks[:,2:3]],axis=1)


def ridge_fit(x,y,case_ids,alpha=.01):
    w=balanced_weights(case_ids).astype(np.float64);w/=w.sum()
    penalty=np.eye(x.shape[1])*alpha;penalty[0,0]=0
    return np.linalg.solve(x.T@(w[:,None]*x)+penalty,x.T@(w*y))
