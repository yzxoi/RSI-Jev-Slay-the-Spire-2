"""E125 small masked actor/critic. Optional PyTorch; no gameplay score input."""
import hashlib
import math

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

ENCODER_VERSION = 'e125-structured-hash-v1'
STATE_DIM, ACTION_DIM, MAX_ACTIONS = 276, 144, 128
HP = dict(lr=3e-4, clip=.2, gamma=1., gae_lambda=.95, epochs=4,
          minibatch=128, entropy=.01, value=.5, grad_norm=.5, target_kl=.03)
OMIT = {'index', 'slot_index', 'target_index', 'card_index', 'seed', 'run_id',
        'after_upgrade', 'description', 'time', 'trace_path'}


def hashed(value, size):
    """Order-independent entity bag; stable keys, never positional action IDs."""
    result = np.zeros(size, dtype=np.float32)
    def add(key, val):
        raw = hashlib.blake2b(key.encode(), digest_size=8).digest()
        result[int.from_bytes(raw[:4], 'little') % size] += val * (1 if raw[4] & 1 else -1)
    def visit(v, path):
        if v is None:
            return
        if isinstance(v, dict):
            for k in sorted(v):
                if k not in OMIT:
                    visit(v[k], path + '/' + k)
        elif isinstance(v, list):
            add(path + '/count', len(v) / 10)
            for item in v:
                ident = str(item.get('id', item.get('name', 'item'))) if isinstance(item, dict) else 'item'
                visit(item, path + '/' + ident)
        elif isinstance(v, bool):
            add(path + '/bool', float(v))
        elif isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError('Nonfinite exported feature')
            add(path + '/number', math.copysign(math.log1p(abs(v)), v) / math.log(101))
        elif isinstance(v, str):
            add(path + '=' + v, 1.)
    visit(value, '')
    return np.clip(result, -4, 4)


def incoming(enemy):
    return sum(max(0, i.get('damage', 0) or 0) * (i.get('hits', 1) or 1)
               for i in enemy.get('intents', []))


def encode(state, choices, previous=None, *, max_actions=MAX_ACTIONS):
    if not 0 < len(choices) <= max_actions:
        raise ValueError('Empty or overflowing legal candidate set')
    if state.get('decision') == 'card_select':
        n = len(state.get('cards', []))
        lo, hi = state.get('min_select', 1), state.get('max_select', 1)
        expected = sum(math.comb(n, k) for k in range(lo, min(n, hi) + 1))
        actual = sum(c['action']['action'] in ('select_cards', 'skip_select') for c in choices)
        if actual != expected:
            raise ValueError('Truncated card selection action space')
    p = state.get('player', {})
    hand, enemies = state.get('hand', []), state.get('enemies', [])
    nums = [p.get('hp', 0) / max(1, p.get('max_hp', 1)), p.get('hp', 0) / 100,
            p.get('max_hp', 0) / 100, p.get('block', 0) / 50,
            state.get('energy', 0) / 5, state.get('max_energy', 0) / 5,
            state.get('round', 0) / 20, len(hand) / 10,
            state.get('draw_pile_count', 0) / 20, state.get('discard_pile_count', 0) / 20,
            len(enemies) / 5, sum(e.get('hp', 0) for e in enemies) / 200,
            sum(e.get('block', 0) for e in enemies) / 50,
            sum(incoming(e) for e in enemies) / 50,
            p.get('deck_size', 0) / 40, len(p.get('potions', [])) / 3,
            len(p.get('relics', [])) / 10, len(choices) / 30,
            state.get('min_select', 0) / 10, state.get('max_select', 0) / 10]
    public = {k: state[k] for k in ('decision', 'hand', 'enemies', 'player', 'player_powers',
              'cards', 'selection_type', 'prompt', 'stars', 'orbs', 'exhaust_pile_count') if k in state}
    # Selection context matters; only semantic metadata from the preceding action.
    public['previous'] = {k: previous[k] for k in ('name', 'card_id') if previous and k in previous}
    s = np.concatenate([np.asarray(nums, dtype=np.float32), hashed(public, 256)])
    actions = []
    for c in choices:
        action, args = c['action']['action'], c['action']['args']
        card = next((x for x in hand if x['index'] == args.get('card_index')), {})
        target = next((x for x in enemies if x['index'] == args.get('target_index')), {})
        potion = next((x for x in p.get('potions', []) if x['index'] == args.get('potion_index')), {})
        selection = []
        if 'indices' in args:
            indexes = {int(x) for x in args['indices'].split(',') if x}
            selection = [x for x in state.get('cards', []) if x['index'] in indexes]
        if action == 'select_card_reward':
            selection = [x for x in state.get('cards', []) if x['index'] == args.get('card_index')]
        stats = card.get('stats') or {}
        previews = card.get('damage_by_target') or []
        damage = next((x.get('damage', 0) for x in previews if x['target_index'] == args.get('target_index')), 0)
        numeric = [float(action == name) for name in ('play_card', 'end_turn', 'use_potion', 'select_cards')]
        numeric += [card.get('cost', 0) / 5, stats.get('damage', 0) / 30,
                    stats.get('block', 0) / 30, (damage or 0) / 30,
                    target.get('hp', 0) / 100, target.get('block', 0) / 30,
                    incoming(target) / 30, len(selection) / 10,
                    stats.get('cards', 0) / 5, stats.get('energy', 0) / 5,
                    stats.get('strengthpower', 0) / 5, stats.get('vulnerablepower', 0) / 5]
        semantic = dict(action=action, card=card, target=target, potion=potion, selection=selection,
                        details=c.get('details'), name=c.get('name'))
        actions.append(np.concatenate([np.asarray(numeric, dtype=np.float32), hashed(semantic, 128)]))
    a = np.stack(actions)
    if s.shape != (STATE_DIM,) or a.shape != (len(choices), ACTION_DIM) or not np.isfinite(s).all() or not np.isfinite(a).all():
        raise ValueError('Invalid encoded observation')
    return s, a


class ActorCritic(nn.Module):
    def __init__(self, state_width=128, action_width=64, state_dim=STATE_DIM, action_dim=ACTION_DIM):
        super().__init__()
        self.config = dict(state_width=state_width, action_width=action_width)
        if (state_dim, action_dim) != (STATE_DIM, ACTION_DIM):
            self.config.update(state_dim=state_dim, action_dim=action_dim)
        self.state = nn.Sequential(nn.Linear(state_dim, state_width), nn.Tanh(),
                                   nn.Linear(state_width, state_width), nn.Tanh())
        self.action = nn.Sequential(nn.Linear(action_dim, action_width), nn.Tanh())
        self.actor = nn.Sequential(nn.Linear(state_width + action_width, action_width),
                                   nn.Tanh(), nn.Linear(action_width, 1))
        self.value = nn.Linear(state_width, 1)
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, math.sqrt(2))
                nn.init.zeros_(module.bias)
        nn.init.orthogonal_(self.actor[-1].weight, .01)
        nn.init.orthogonal_(self.value.weight, 1.)

    def forward(self, states, actions, mask):
        if not mask.any(-1).all():
            raise ValueError('No legal action in padded batch')
        s, a = self.state(states), self.action(actions)
        logits = self.actor(torch.cat([s[:, None, :].expand(-1, a.shape[1], -1), a], -1)).squeeze(-1)
        return Categorical(logits=logits.masked_fill(~mask, torch.finfo(logits.dtype).min)), self.value(s).squeeze(-1)


def padded(observations):
    n = max(len(a) for _, a in observations)
    states = torch.from_numpy(np.stack([s for s, _ in observations]))
    action_dim = observations[0][1].shape[1]
    if any(a.shape[1] != action_dim for _, a in observations):
        raise ValueError('Mixed encoder action dimensions')
    actions = torch.zeros(len(observations), n, action_dim)
    mask = torch.zeros(len(observations), n, dtype=torch.bool)
    for i, (_, a) in enumerate(observations):
        actions[i, :len(a)] = torch.from_numpy(a)
        mask[i, :len(a)] = True
    return states, actions, mask


def advantages(rewards, values, terminated=True, bootstrap=0., gamma=1., lam=.95):
    if len(rewards) != len(values) or not rewards:
        raise ValueError('Invalid trajectory')
    gae, result = 0., np.zeros(len(rewards), dtype=np.float32)
    for t in reversed(range(len(rewards))):
        nxt = (0. if terminated else bootstrap) if t == len(rewards) - 1 else values[t+1]
        gae = rewards[t] + gamma * nxt - values[t] + gamma * lam * gae
        result[t] = gae
    return result, result + np.asarray(values, dtype=np.float32)


def clipped_policy_loss(logprob, old_logprob, advantage, clip=.2):
    ratio = (logprob - old_logprob).exp()
    return -torch.minimum(ratio * advantage, ratio.clamp(1-clip, 1+clip) * advantage).mean()


def update(model, optimizer, episodes, rng, hp=None):
    hp = HP if hp is None else {**HP, **hp}
    records, advs, returns = [], [], []
    for trajectory, reward in episodes:
        values = [x['value'] for x in trajectory]
        adv, ret = advantages([0.] * (len(values)-1) + [reward], values,
                              gamma=hp['gamma'], lam=hp['gae_lambda'])
        records.extend(trajectory); advs.extend(adv); returns.extend(ret)
    obs = [x['encoded'] for x in records]
    old = torch.tensor([x['logprob'] for x in records])
    chosen = torch.tensor([x['index'] for x in records])
    adv = torch.tensor(np.asarray(advs)); ret = torch.tensor(np.asarray(returns))
    adv = (adv - adv.mean()) / (adv.std(unbiased=False) + 1e-8)
    metrics = []; stopped = False
    for epoch in range(hp['epochs']):
        indices = rng.permutation(len(records))
        for offset in range(0, len(records), hp['minibatch']):
            ix = indices[offset:offset + hp['minibatch']]
            dist, value = model(*padded([obs[i] for i in ix]))
            lp = dist.log_prob(chosen[ix])
            logratio = lp - old[ix]; ratio = logratio.exp()
            kl = ((ratio - 1) - logratio).mean()
            if kl.item() > hp['target_kl']:
                stopped = True
                break
            pg = clipped_policy_loss(lp, old[ix], adv[ix], hp['clip'])
            vl = .5 * (value - ret[ix]).square().mean()
            ent = dist.entropy().mean()
            loss = pg + hp['value'] * vl - hp['entropy'] * ent
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite PPO loss')
            optimizer.zero_grad(); loss.backward()
            norm = nn.utils.clip_grad_norm_(model.parameters(), hp['grad_norm'], error_if_nonfinite=True)
            optimizer.step()
            metrics.append(dict(loss=loss.item(), policy_loss=pg.item(), value_loss=vl.item(),
                                entropy=ent.item(), kl=kl.item(), grad_norm=norm.item(),
                                clip_fraction=((ratio-1).abs() > hp['clip']).float().mean().item()))
        if stopped:
            break
    if not metrics:
        raise ValueError('PPO made no finite optimizer step')
    return {'transitions': len(records), 'minibatches': len(metrics), 'kl_early_stop': stopped,
            **{key: float(np.mean([x[key] for x in metrics])) for key in metrics[0]}}
