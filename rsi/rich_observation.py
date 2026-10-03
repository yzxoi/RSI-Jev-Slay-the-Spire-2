"""Opt-in E141 internal observations; retains entity order and excludes seed IDs."""
import numpy as np
from .phase_rl import phase_encode, semantics, STATE_SIZE, ACTION_SIZE
from .ppo import ActorCritic, hashed

SCHEMA = 'e141-internal-v1'
ENCODER = 'e141-ordered-internal-v1'
STATE_DIM, ACTION_DIM = STATE_SIZE + 524, ACTION_SIZE + 128


def observe(engine, state):
    extra = engine.send({'cmd': 'get_learning_observation'})
    if extra.get('schema') != SCHEMA:
        raise ValueError('Unsupported learning observation schema')
    return {**state, 'learning': extra}


def ordered(value):
    """Explicit paths preserve position; legacy bag hashing otherwise drops order."""
    if isinstance(value, list):
        return {f'position_{i}': ordered(v) for i, v in enumerate(value)}
    if isinstance(value, dict):
        return {k: ordered(v) for k, v in value.items()}
    return value


def rich_encode(state, choices, previous=None, **kwargs):
    extra = state.get('learning')
    if not extra or extra.get('schema') != SCHEMA:
        raise ValueError('E141 encoder requires the explicit internal observation')
    s, a = phase_encode(state, choices, previous, **kwargs)
    piles = extra.get('piles') or {}; osty = extra.get('osty') or {}
    game_map = extra.get('map') or {}; coord = game_map.get('current_coord') or {}
    nodes = [n for row in game_map.get('rows', []) for n in row]
    nums = [osty.get('hp', 0)/100, osty.get('max_hp', 0)/100, osty.get('block', 0)/50,
            osty.get('alive', False), extra.get('orb_slots', 0)/10, extra.get('stars', 0)/20,
            *(len(piles.get(p, []))/40 for p in ('draw', 'discard', 'exhaust')),
            len(nodes)/100, coord.get('row', -1)/20, coord.get('col', -1)/10]
    s = np.concatenate((s, np.asarray(nums, dtype=np.float32), hashed(ordered(semantics(extra)), 512)))
    action_extras = []
    for choice in choices:
        args = choice['action']['args']
        node = next((n for n in nodes if n['col'] == args.get('col') and n['row'] == args.get('row')), None)
        action_extras.append(hashed(ordered({'route_node': node}), 128))
    return s, np.concatenate((a, np.stack(action_extras)), axis=1)


def extend_model(source):
    model = ActorCritic(state_width=source.config['state_width'], action_width=source.config['action_width'],
                       state_dim=STATE_DIM, action_dim=ACTION_DIM)
    old = source.state_dict(); new = model.state_dict()
    for key in new:
        if key in ('state.0.weight', 'action.0.weight'):
            new[key].zero_(); new[key][:, :old[key].shape[1]] = old[key]
        else:
            new[key].copy_(old[key])
    model.load_state_dict(new)
    return model
