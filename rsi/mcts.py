"""Small deterministic action-tree search; no game rules or model calls here.

Every node belongs to an action HISTORY. Observation hashes detect divergence,
but are never used to merge nodes with potentially different hidden RNG state.
Only completed engine trajectories supply values. UCT means are search
statistics, not calibrated win probabilities. Execution uses a verified incumbent.
"""
from dataclasses import dataclass, field
import math

from .trace import digest


@dataclass
class Node:
    observation: str | None = None
    visits: int = 0
    total: float = 0.0
    children: dict = field(default_factory=dict)
    actions: list | None = None

    def bind(self, state_hash):
        if self.observation is not None and self.observation != state_hash:
            raise ValueError('Revisited action history produced a different observation')
        self.observation = state_hash

    def initialize(self, choices, rng):
        keys = [digest(c['action']) for c in choices]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate actions')
        if self.actions is None:
            self.actions = list(choices)
            rng.shuffle(self.actions)
            self.children = {digest(c['action']): Node() for c in self.actions}
        elif set(keys) != set(self.children):
            raise ValueError('Legal actions changed at the same action history')


class UCT:
    def __init__(self, rng):
        self.rng = rng
        self.root = Node()
        self.max_depth = 0

    def choose(self, node, state_hash, choices):
        node.bind(state_hash)
        node.initialize(choices, self.rng)
        unvisited = [c for c in node.actions if not node.children[digest(c['action'])].visits]
        if unvisited:
            choice = unvisited[0]
        else:
            def upper(choice):
                child = node.children[digest(choice['action'])]
                return child.total / child.visits + math.sqrt(
                    2 * math.log(max(1, node.visits)) / child.visits)
            choice = max(node.actions, key=upper)
        child = node.children[digest(choice['action'])]
        return choice, child, child.visits == 0

    def backup(self, path, reward):
        if not 0 <= reward <= 1:
            raise ValueError('UCT requires bounded terminal utility')
        for node in path:
            node.visits += 1
            node.total += reward
        self.max_depth = max(self.max_depth, len(path) - 1)

    def summary(self):
        return {'max_tree_depth': self.max_depth, 'root_completed_visits': self.root.visits,
                'root': [{'action': c['action'],
                          'visits': self.root.children[digest(c['action'])].visits,
                          'mean_utility': (self.root.children[digest(c['action'])].total /
                                           self.root.children[digest(c['action'])].visits
                                           if self.root.children[digest(c['action'])].visits else None)}
                         for c in self.root.actions or []]}


class Flat:
    """Balanced ROOT allocation, followed by the same rollout policy as UCT."""
    def __init__(self, rng):
        self.rng = rng
        self.root = Node()
        self.attempts = 0

    def choose(self, state_hash, choices):
        self.root.bind(state_hash)
        self.root.initialize(choices, self.rng)
        choice = self.root.actions[self.attempts % len(self.root.actions)]
        self.attempts += 1
        return choice, self.root.children[digest(choice['action'])]

    def backup(self, path, reward):
        if not 0 <= reward <= 1:
            raise ValueError('Flat MC requires bounded terminal utility')
        for node in path:
            node.visits += 1
            node.total += reward

    def summary(self):
        return {'root_attempts': self.attempts, **UCT.summary(self)}

    max_depth = 1
