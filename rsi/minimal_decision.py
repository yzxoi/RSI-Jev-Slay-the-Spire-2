"""E116 synthetic layered decision worlds; no game or model dependencies."""
import copy
import hashlib
import json
import random


HORIZONS = (4, 8, 16)
SEEDS = tuple(f'e116_20260929_{i:03d}' for i in range(1, 13))
ARMS = ('choice', 'prediction', 'assisted', 'flip', 'sham', 'readout')
MODEL = 'typesafe/jev-1.13'
ENDPOINT = 'https://openrouter.ai/api/v1/systemone'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rng_for(*parts):
    return random.Random(int(digest(parts), 16))


def solve(world, boundary=None):
    """Exact undiscounted terminal-payoff DP; optional exact boundary replacement."""
    layers = world['layers']
    end = world['horizon'] if boundary is None else boundary['layer']
    values = dict(world['payoffs'] if boundary is None else boundary['values'])
    actions = {}
    for layer in reversed(layers[:end]):
        for state in layer:
            q = {a: values[nxt] for a, nxt in world['edges'][state].items()}
            actions[state] = q
            values[state] = max(q.values())
    return values, actions


def reachable(world, state):
    """Independent forward set propagation (no backward value recursion)."""
    current = {state}
    while any(s in world['edges'] for s in current):
        current = {nxt for s in current for nxt in world['edges'][s].values()}
    return current


def rollout(world, route):
    assert len(route) == world['horizon']
    state = world['start']
    for a in route:
        state = world['edges'][state][a]
    return state, world['payoffs'][state]


def best(q):
    assert q['A'] != q['B'], 'root must have a unique optimum'
    return max(q, key=q.get)


def optimal_witness(world, q):
    state = world['start']
    route, consequential_layers = [], []
    for t in range(world['horizon']):
        a = max(('A', 'B'), key=lambda x: q[state][x])
        if q[state]['A'] != q[state]['B']:
            consequential_layers.append(t)
        route.append(a)
        state = world['edges'][state][a]
    return route, consequential_layers


def generate(seed, horizon, root_answer, prediction_true):
    rng = rng_for(seed, horizon, 'world-v1')
    for attempt in range(1, 10001):
        # Both root alternatives retain a separate four-state component. IDs and
        # row positions reveal neither component membership nor payoff rank.
        ids = rng.sample(range(1000, 9999), 1 + 8 * horizon)
        start = f's{ids[0]}'
        layers = [[start]] + [[f's{x}' for x in ids[1+8*t:1+8*(t+1)]]
                             for t in range(horizon)]
        edges = {start: {'A': rng.choice(layers[1][:4]), 'B': rng.choice(layers[1][4:])}}
        for t in range(1, horizon):
            for lane in (0, 1):
                for state in layers[t][4*lane:4*lane+4]:
                    dest = rng.sample(layers[t+1][4*lane:4*lane+4], 2)
                    edges[state] = dict(zip(('A', 'B'), dest))
        rewards = list(range(8)); rng.shuffle(rewards)
        world = {'horizon': horizon, 'start': start, 'layers': layers,
                 'edges': edges, 'payoffs': dict(zip(layers[-1], rewards))}
        values, q = solve(world)
        root_q = q[start]
        if root_q['A'] == root_q['B']:
            continue
        if best(root_q) != root_answer:
            edges[start]['A'], edges[start]['B'] = edges[start]['B'], edges[start]['A']
            values, q = solve(world)
        witness, meaningful = optimal_witness(world, q)
        if len([t for t in meaningful if t > 0]) < 2:
            continue
        root_reachable = {a: reachable(world, s) for a, s in edges[start].items()}
        flip = copy.deepcopy(world)
        top = [max(root_reachable[a], key=world['payoffs'].get) for a in ('A', 'B')]
        flip['payoffs'][top[0]], flip['payoffs'][top[1]] = (
            flip['payoffs'][top[1]], flip['payoffs'][top[0]])
        if best(solve(flip)[1][start]) == root_answer:
            continue
        # Swap two non-root-optimal terminals. Certify the sham, rather than
        # assuming any low-payoff edit preserves the optimum.
        pairs = [(a, b) for i, a in enumerate(layers[-1]) for b in layers[-1][i+1:]]
        rng.shuffle(pairs)
        sham = None
        for a, b in pairs:
            candidate = copy.deepcopy(world)
            candidate['payoffs'][a], candidate['payoffs'][b] = (
                candidate['payoffs'][b], candidate['payoffs'][a])
            cq = solve(candidate)[1][start]
            if cq['A'] != cq['B'] and best(cq) == root_answer:
                sham = candidate
                break
        if sham is None:
            continue
        route_rng = rng_for(seed, horizon, 'route-v1')
        route = None
        for _ in range(10000):
            candidate_route = [route_rng.choice(('A', 'B')) for _ in range(horizon)]
            if (rollout(world, candidate_route)[1] >= 4) == prediction_true:
                route = candidate_route
                break
        if route is None:
            continue
        # Sort opaque labels for rendering. Hidden array partitions are not sent.
        for w in (world, flip, sham):
            w['layers'] = [sorted(layer) for layer in w['layers']]
        midpoint = horizon // 2
        boundary = {'layer': midpoint, 'values': {s: values[s] for s in world['layers'][midpoint]}}
        assert solve(world, boundary)[1][start] == q[start]
        return {'id': f'{seed}_h{horizon}', 'seed': seed, 'horizon': horizon,
                'world': world, 'flip_world': flip, 'sham_world': sham,
                'route': route, 'prediction_answer': 'A' if prediction_true else 'B',
                'boundary': boundary, 'attempts': attempt,
                'certificate': {'root_q': q[start], 'answer': root_answer,
                    'flip_q': solve(flip)[1][start], 'sham_q': solve(sham)[1][start],
                    'witness': witness, 'consequential_layers': meaningful,
                    'route_terminal': rollout(world, route)[0],
                    'route_payoff': rollout(world, route)[1]}}
    raise RuntimeError(f'Generator failed after 10000 attempts: {seed}/{horizon}')


def render(world):
    return {'rules': 'A deterministic layered graph. At each step choose A or B. '
            'All transitions are listed. Only the final state pays its listed payoff; '
            'there are no other rewards, costs, hidden rules or random events. '
            'Later actions can be chosen freely to maximize final payoff.',
            'steps': world['horizon'], 'start': world['start'],
            'transitions_by_step': [[{'state': s, **world['edges'][s]} for s in layer]
                                    for layer in world['layers'][:-1]],
            'terminal_payoffs': dict(sorted(world['payoffs'].items()))}


def request(item, arm):
    world = item['world'] if arm not in ('flip', 'sham') else item[arm + '_world']
    state = render(world)
    criteria = {'A': 'Choose A as the first action.', 'B': 'Choose B as the first action.'}
    instruction = ('Choose the first action allowing the largest achievable final payoff, '
                   'assuming all later actions are chosen optimally. Use the supplied complete rules.')
    if arm == 'prediction':
        state['prescribed_actions'] = item['route']
        instruction = ('Follow exactly the prescribed_actions from start; do not optimize or change them. '
                       'Is the final payoff at least 4? Choose A for yes and B for no.')
        criteria = {'A': 'Yes: final payoff is at least 4.', 'B': 'No: final payoff is below 4.'}
    elif arm == 'assisted':
        state['verified_midpoint_values'] = item['boundary']
        state['assistance_definition'] = ('For each state after the indicated number of actions, '
            'values gives the exact maximum final payoff achievable from there. '
            'These are verified results of solving the remaining graph, not additional rewards.')
    elif arm == 'readout':
        state = {'exact_maximum_final_payoff_after_first_action': item['certificate']['root_q']}
        instruction = 'Choose the first action with the larger exact maximum final payoff in the supplied table.'
    elif arm not in ARMS:
        raise ValueError(arm)
    return {'model': MODEL, 'state': state, 'questions': {'answer': {
        'type': 'choice', 'instructions': instruction, 'criteria': criteria}}}


def answer_key(item, arm):
    if arm == 'prediction':
        return item['prediction_answer']
    q = item['certificate'].get(arm + '_q', item['certificate']['root_q'])
    return best(q)


def make_bank():
    items = []
    for h in HORIZONS:
        root_labels = ['A'] * 6 + ['B'] * 6
        route_labels = [True] * 6 + [False] * 6
        rng_for(h, 'root-balance').shuffle(root_labels)
        rng_for(h, 'route-balance').shuffle(route_labels)
        for seed, root, pred in zip(SEEDS, root_labels, route_labels):
            items.append(generate(seed, h, root, pred))
    cells = [{'item_id': item['id'], 'arm': arm} for item in items for arm in ARMS]
    rng_for('e116-order-v1').shuffle(cells)
    return {'schema': 1, 'seeds': SEEDS, 'horizons': HORIZONS, 'arms': ARMS,
            'items': items, 'schedule': cells}


def verify_bank(bank):
    checks = 0
    for item in bank['items']:
        for field in ('world', 'flip_world', 'sham_world'):
            world = item[field]
            values, qs = solve(world)
            seen = set()
            for t, layer in enumerate(world['layers']):
                assert not seen.intersection(layer)
                seen.update(layer)
                if t < world['horizon']:
                    for s in layer:
                        assert set(world['edges'][s]) == {'A', 'B'}
                        assert set(world['edges'][s].values()) <= set(world['layers'][t+1])
                        expected = max(world['payoffs'][x] for x in reachable(world, s))
                        assert values[s] == expected
                        checks += 1
            for a, dest in world['edges'][world['start']].items():
                assert qs[world['start']][a] == max(world['payoffs'][x] for x in reachable(world, dest))
            cert_key = {'world': 'root_q', 'flip_world': 'flip_q', 'sham_world': 'sham_q'}[field]
            assert qs[world['start']] == item['certificate'][cert_key]
        base = item['world']
        for field in ('flip_world', 'sham_world'):
            other = item[field]
            assert base['edges'] == other['edges'] and base['layers'] == other['layers']
            assert sum(base['payoffs'][s] != other['payoffs'][s] for s in base['payoffs']) == 2
        assert answer_key(item, 'choice') != answer_key(item, 'flip')
        assert answer_key(item, 'choice') == answer_key(item, 'sham')
        assert solve(base, item['boundary'])[1][base['start']] == item['certificate']['root_q']
        assert (rollout(base, item['route'])[1] >= 4) == (item['prediction_answer'] == 'A')
        assert len([t for t in item['certificate']['consequential_layers'] if t > 0]) >= 2
        for arm in ARMS:
            assert 'certificate' not in request(item, arm)['state']
    for h in HORIZONS:
        group = [x for x in bank['items'] if x['horizon'] == h]
        assert len(group) == 12
        for arm in ARMS:
            assert sum(answer_key(x, arm) == 'A' for x in group) == 6
    expected = {(i['id'], a) for i in bank['items'] for a in ARMS}
    assert len(bank['schedule']) == len(expected)
    assert {(c['item_id'], c['arm']) for c in bank['schedule']} == expected
    return {'passed': True, 'forward_value_checks': checks, 'items': len(bank['items']),
            'cells': len(bank['schedule']), 'generation_attempts': sum(x['attempts'] for x in bank['items'])}
