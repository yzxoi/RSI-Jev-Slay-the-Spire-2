"""E128 frozen-network PUCT; independent engine replay for each new tree edge."""
from dataclasses import dataclass, field
import math
import time
import uuid
import numpy as np
import torch
from .battle_search import boundary, choices_for, compact, finish, outcome
from .engine import ROOT, Headless
from .ppo import encode, padded
from .ppo_env import reward_for
from .trace import Trace, digest


def normalized(value):
    if not math.isfinite(value): raise ValueError('Nonfinite leaf value')
    return max(0.,min(1.,(value+1)/2.25))


def inference(model,state,previous):
    choices=choices_for(state)
    with torch.inference_mode():
        dist,v=model(*padded([encode(state,choices,previous)]))
    return choices,dist.probs[0].numpy().astype(float),float(v[0])


@dataclass
class Edge:
    choice: dict
    prior: float
    child: object=None
    visits: int=0
    total: float=0.


@dataclass
class Node:
    state: dict
    previous: object
    value: float
    edges: list=field(default_factory=list)
    terminal: bool=False
    visits: int=0

    def select(self,c=1.5):
        return max(enumerate(self.edges),key=lambda x:(
            (x[1].total/x[1].visits if x[1].visits else self.value)+
            c*x[1].prior*math.sqrt(self.visits+1)/(1+x[1].visits),-x[0]))[1]


class PUCT:
    """Single-player backup: value signs never alternate with action depth."""
    def __init__(self,root,expand,max_depth=8):
        self.root,self.expand,self.max_depth=root,expand,max_depth
        self.maximum_depth=0;self.cache_hits=0

    def simulate(self):
        node=self.root;nodes=[node];edges=[]
        while not node.terminal and len(edges)<self.max_depth:
            edge=node.select();edges.append(edge)
            if edge.child is None:
                edge.child=self.expand(edges)
                node=edge.child;nodes.append(node);break
            node=edge.child;nodes.append(node)
        else:
            self.cache_hits+=1
        value=node.value
        for n in nodes:n.visits+=1
        for e in edges:e.visits+=1;e.total+=value
        self.maximum_depth=max(self.maximum_depth,len(edges))

    def selected(self):
        return max(enumerate(self.root.edges),key=lambda x:(x[1].visits,
            x[1].total/x[1].visits if x[1].visits else -float('inf'),x[1].prior,-x[0]))[1].choice

    def statistics(self):
        return dict(simulations=self.root.visits,depth=self.maximum_depth,cache_hits=self.cache_hits,
            edges=[dict(action=e.choice['action'],prior=e.prior,visits=e.visits,
                        q=e.total/e.visits if e.visits else None) for e in self.root.edges])


def make_node(model,state,previous,value=None):
    if boundary(state):return Node(state,previous,normalized(reward_for(outcome(state))),terminal=True)
    choices,priors,pred=inference(model,state,previous)
    return Node(state,previous,normalized(pred if value is None else value),
                [Edge(c,float(p)) for c,p in zip(choices,priors)])


class SearchPolicy:
    def __init__(self,frozen,manifest,model,mode):
        if mode not in ('value','rollout'):raise ValueError('Unknown leaf evaluator')
        self.frozen,self.manifest,self.model,self.mode=frozen,manifest,model,mode
        self.rounds=set();self.roots=[];self.probes=[]

    def __call__(self,state,choices,previous,history):
        _,probs,pred=inference(self.model,state,previous)
        greedy=choices[int(np.argmax(probs))]
        turn=state.get('round')
        if state['decision']!='combat_play' or turn in self.rounds or len(self.rounds)>=6:
            return greedy,dict(source='greedy_actor',probabilities=probs.tolist(),value=pred)
        self.rounds.add(turn);started=time.monotonic();deadline=started+60
        root=make_node(self.model,state,previous)
        def expand(path):
            leaf,prev,value,record=self.probe(state,history,path,deadline)
            self.probes.append(record)
            if record['status'] in ('timeout', 'action_cap'):
                raise TimeoutError(f"Search probe censored: {record['status']}")
            if record['status'] not in ('leaf','clear','defeat'):
                raise RuntimeError(f"Search probe {record['status']}: {record.get('error','')}")
            return make_node(self.model,leaf,prev,value)
        tree=PUCT(root,expand)
        for _ in range(16):
            if time.monotonic()>=deadline:raise TimeoutError('Search root time cap')
            tree.simulate()
        chosen=tree.selected()
        record=dict(round=turn,before=digest(state),mode=self.mode,seconds=time.monotonic()-started,
                    changed_from_actor=chosen['action']!=greedy['action'],**tree.statistics())
        self.roots.append(record)
        return chosen,dict(source='puct_'+self.mode,probabilities=probs.tolist(),value=pred,search=record)

    def probe(self,root_state,history,path,root_deadline):
        started=time.monotonic();deadline=min(root_deadline,started+15)
        trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**self.manifest,'scope':'E128_simulation',
                    'case':self.frozen['case'],'mode':self.mode,'root_hash':digest(root_state),
                    'committed_history_hash':digest(history)})
        result=dict(status='error',steps=0,replay_seconds=0.,depth=len(path),entry_verified=False)
        engine=None;state={};leaf={};previous=self.frozen['previous'];leaf_previous=None;value=None
        def send(command):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Search simulation cap')
            engine.timeout=min(10,remaining);return engine.send(command)
        try:
            if digest(self.frozen['prefix'])!=self.frozen['prefix_hash']:raise ValueError('Changed reset prefix')
            engine=Headless(trace.directory,timeout=10,resource_decisions=True)
            for cmd in self.frozen['prefix']:state=send(cmd)
            if digest(state)!=self.frozen['entry_hash']:raise ValueError('Reset mismatch')
            for h in history:
                if digest(state)!=h['before']:raise ValueError('History before mismatch')
                chosen=next(c for c in choices_for(state) if c['action']==h['action'])
                state=send(chosen['action']);previous=chosen
                if digest(state)!=h['after']:raise ValueError('History after mismatch')
            if digest(state)!=digest(root_state):raise ValueError('Root mismatch')
            result.update(entry_verified=True,replay_seconds=time.monotonic()-started)
            for edge in path:
                cs=choices_for(state)
                chosen=next(c for c in cs if c['action']==edge.choice['action'])
                trace.write('decision',dict(before=digest(state),candidates=cs,chosen=chosen,source='tree'))
                state=send(chosen['action']);previous=chosen;result['steps']+=1
                if edge.child and digest(state)!=digest(edge.child.state):raise ValueError('Tree transition mismatch')
            leaf=state;leaf_previous=previous
            if boundary(leaf):
                value=reward_for(outcome(leaf));result.update(status=boundary(leaf),leaf_terminal=True,
                                                           leaf_prediction=value,return_value=value)
            else:
                _,_,prediction=inference(self.model,leaf,previous)
                result.update(leaf_terminal=False,leaf_prediction=prediction)
                if self.mode=='value':
                    value=prediction;result.update(status='leaf',return_value=value)
                else:
                    for step in range(121):
                        if boundary(state):
                            value=reward_for(outcome(state));result.update(status=boundary(state),return_value=value,
                                    rollout_steps=step,squared_error=(prediction-value)**2);break
                        if step==120:result['status']='action_cap';break
                        cs,ps,_=inference(self.model,state,previous);chosen=cs[int(np.argmax(ps))]
                        trace.write('decision',dict(before=digest(state),candidates=cs,chosen=chosen,source='actor_rollout'))
                        state=send(chosen['action']);previous=chosen;result['steps']+=1
            result.update(leaf_hash=digest(leaf),final_hash=digest(state))
        except TimeoutError as exc:result.update(status='timeout',error=str(exc))
        except Exception as exc:result.update(status='error',error=f'{type(exc).__name__}: {exc}')
        finish(trace,result,engine,started)
        return leaf,leaf_previous,value,compact(result)
