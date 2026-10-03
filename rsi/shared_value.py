"""E152 shared entity attributes pooled by role; opt-in critic inputs only.

This is a lossy compositional feature baseline, not a mechanic simulator or a
language model. Numeric channels never include card IDs in their feature keys.
"""
from functools import lru_cache
import hashlib
import math
import re

import numpy as np
import torch
from torch import nn

from .ppo import incoming
from .task_value import PHASES

ENCODER = 'e152-shared-attributes-v1'
ROLES = ('hand', 'deck', 'enemies', 'powers', 'potions', 'relics', 'offers')
SCALES = (5., 20., 3., 5., 3., 5., 5.)
SIZE = 540
STOP = frozenset('the a an to of and your you is are at on in this that it for diff plural'.split())


@lru_cache(maxsize=32768)
def bucket(key, size):
    b = hashlib.blake2b(key.encode(), digest_size=8).digest()
    return int.from_bytes(b[:4], 'little') % size, 1 if b[4] & 1 else -1


def number(value):
    if value is None:
        return 0.
    x = float(value)
    if not math.isfinite(x):
        raise ValueError('Nonfinite shared attribute')
    return x


def entity(obj, kind):
    stats = obj.get('stats') or {}
    s = lambda key: number(stats.get(key))
    kind_cost = obj.get('card_cost', obj.get('cost', 0)) if kind == 'card' else 0
    numeric = [number(kind_cost)/5, s('damage')/30, s('block')/30,
        s('cards')/5, s('energy')/5, s('strengthpower')/5,
        s('dexteritypower')/5, s('vulnerablepower')/5, s('weakpower')/5,
        number(obj.get('hp'))/100, number(obj.get('max_hp'))/100,
        number(obj.get('block'))/50, incoming(obj)/50,
        number(obj.get('amount', obj.get('stacks', 0)))/10,
        bool(obj.get('can_play')), bool(obj.get('upgraded')),
        obj.get('type') == 'Attack', obj.get('type') == 'Skill', obj.get('type') == 'Power',
        kind == 'card', kind == 'potion', kind == 'relic', kind == 'enemy']
    generic = np.zeros(16, dtype=np.float32)
    attrs = {**stats, **(obj.get('vars') or {})}
    if 'card_cost' in obj or kind in ('potion', 'relic'):
        attrs['price'] = obj.get('cost', 0)
    for key, value in sorted(attrs.items()):
        if value is None or not isinstance(value, (int, float)):
            continue
        n = number(value)
        i, sign = bucket(str(key).lower(), 16)
        generic[i] += sign * math.copysign(math.log1p(abs(n)), n) / math.log(101)
    texts = [str(obj.get(k) or '') for k in ('name', 'description', 'type', 'rarity', 'target_type')]
    texts += [str(k) for k in obj.get('keywords') or []]
    for power in obj.get('powers') or []:
        texts += [str(power.get('name') or ''), str(power.get('description') or '')]
        i, sign = bucket('power:' + str(power.get('name', '')), 16)
        generic[i] += sign * number(power.get('amount', power.get('stacks', 0))) / 10
    tokens = set(re.findall(r'[a-z]+', ' '.join(texts).lower())) - STOP
    lexical = np.zeros(32, dtype=np.float32)
    for token in sorted(tokens):
        i, sign = bucket(token, 32)
        lexical[i] += sign / max(1., math.sqrt(len(tokens)))
    out = np.concatenate(([1.], numeric, generic, lexical)).astype(np.float32)
    if out.shape != (72,) or not np.isfinite(out).all():
        raise ValueError('Invalid entity feature')
    return out


def shared_encode(state, legacy):
    """Uses current observation plus the 20 existing scalar features only."""
    if np.asarray(legacy).shape != (SIZE,):
        raise ValueError('Expected E140 state vector')
    p = state.get('player') or {}
    c = state.get('context') or {}
    offers = [('card', x) for x in state.get('cards') or []]
    offers += [('potion', x) for x in state.get('potions') or []]
    offers += [('relic', x) for x in state.get('relics') or []]
    if state.get('potion'):
        offers.append(('potion', state['potion']))
    for b in state.get('bundles') or []:
        offers += [('card', x) for x in b.get('cards') or []]
    offers += [('option', x) for x in state.get('options') or []]
    offers += [('option', x) for x in state.get('choices') or []]
    groups = [[('card', x) for x in state.get('hand') or []],
        [('card', x) for x in p.get('deck') or []],
        [('enemy', x) for x in state.get('enemies') or []],
        [('power', x) for x in state.get('player_powers') or []],
        [('potion', x) for x in p.get('potions') or []],
        [('relic', x) for x in p.get('relics') or []], offers]
    globals_ = np.concatenate([legacy[:20],
        np.asarray([state['decision'] == ph for ph in PHASES], dtype=np.float32),
        [c.get('act', 0)/3, c.get('floor', 0)/17, p.get('gold', 0)/300,
         p.get('potion_capacity', 0)/3, (state.get('card_removal_cost') or 0)/200,
         bool(state.get('can_skip')), len(offers)/10]])
    pools = []
    for objects, scale in zip(groups, SCALES):
        pool = np.zeros(72, dtype=np.float32)
        for kind, obj in objects:
            pool += entity(obj, kind)
        pools.append(np.clip(pool / scale, -4, 4))
    out = np.concatenate([globals_, *pools]).astype(np.float32)
    if out.shape != (SIZE,) or not np.isfinite(out).all():
        raise ValueError('Invalid shared state')
    return out


class ValueMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(545, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh())
        self.value = nn.Linear(128, 1)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, math.sqrt(2))
                nn.init.zeros_(m.bias)
        nn.init.zeros_(self.value.weight)

    def forward(self, x):
        return self.value(self.state(x)).squeeze(-1)
