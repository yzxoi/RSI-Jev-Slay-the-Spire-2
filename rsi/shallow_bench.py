"""E118: fresh short-horizon worlds and fixed multi-model requests."""
import json
from .minimal_decision import canonical, digest, rng_for, solve, reachable, rollout, best, optimal_witness, render

SEEDS = tuple(f'e118_20260929_{i:03d}' for i in range(1, 9))
HORIZONS = (1, 2, 4, 8)
TASKS = ('choice', 'predict_yes_a', 'predict_yes_b')
CONFIGS = {
    'jev': dict(model='typesafe/jev-1.13', canonical='typesafe/jev-1.13-20260917',
                provider='TypeSafe', cap=.20, effort=None),
    'sol_none': dict(model='openai/gpt-6-sol', canonical='openai/gpt-6-sol-20260922',
        provider='OpenAI', slug='openai', ignore=['openai/flex', 'openai/fast'],
        cap=.50, effort='none', input_price=.0000025, output_price=.00001, prompt_max=2, completion_max=10),
    'sol_low': dict(model='openai/gpt-6-sol', canonical='openai/gpt-6-sol-20260922',
        provider='OpenAI', slug='openai', ignore=['openai/flex', 'openai/fast'],
        cap=.80, effort='low', input_price=.0000025, output_price=.00001, prompt_max=2, completion_max=10),
    'sonnet_low': dict(model='anthropic/claude-sonnet-5.5', canonical='anthropic/claude-sonnet-5.5-20260928',
        provider='Anthropic', slug='anthropic', ignore=[],
        cap=1.00, effort='low', input_price=.000004, output_price=.00001, prompt_max=2, completion_max=10),
    'gemini_low': dict(model='google/gemini-3.8-flash', canonical='google/gemini-3.8-flash-20260902',
        provider='Google AI Studio', slug='google-ai-studio', ignore=['google-ai-studio/flex', 'google-ai-studio/priority'],
        cap=.50, effort='low', input_price=.00000075, output_price=.00000375, prompt_max=.75, completion_max=3.75),
    'deepseek_low': dict(model='deepseek/deepseek-v4.1-flash', canonical='deepseek/deepseek-v4.1-flash-20260910',
        provider='DeepInfra', slug='deepinfra/fp8', ignore=[],
        cap=.25, effort='low', input_price=.00000014, output_price=.00000042, prompt_max=.14, completion_max=.42),
    'qwen_low': dict(model='qwen/qwen3.8-max-0902', canonical='qwen/qwen3.8-max-20260902',
        provider='Alibaba', slug='alibaba', ignore=[],
        cap=.95, effort='low', input_price=.0000025, output_price=.000006, prompt_max=2, completion_max=6),
    'kimi_low': dict(model='moonshotai/kimi-k3', canonical='moonshotai/kimi-k3-20260715',
        provider='Moonshot AI', slug='moonshotai/mxfp4', ignore=[],
        cap=1.40, effort='low', input_price=.000003, output_price=.000015, prompt_max=3, completion_max=15),
}
INITIAL_CONFIGS = ('jev', 'sol_none', 'sol_low', 'sonnet_low', 'gemini_low')
REPLACEMENT_CONFIGS = ('deepseek_low', 'qwen_low', 'kimi_low')


def generate(seed, h, root_label, route_truth):
    rng = rng_for(seed, h, 'e118-v1')
    for attempt in range(1, 10001):
        names = [f's{x}' for x in rng.sample(range(1000, 9999), 1+8*h)]
        layers = [[names[0]]] + [names[1+8*t:1+8*(t+1)] for t in range(h)]
        edges = {names[0]: {'A': rng.choice(layers[1][:4]), 'B': rng.choice(layers[1][4:])}}
        for t in range(1, h):
            for lane in (0, 1):
                for s in layers[t][4*lane:4*lane+4]:
                    edges[s] = dict(zip(('A', 'B'), rng.sample(layers[t+1][4*lane:4*lane+4], 2)))
        payoffs = list(range(8)); rng.shuffle(payoffs)
        w = dict(start=names[0], horizon=h, layers=layers, edges=edges, payoffs=dict(zip(layers[-1], payoffs)))
        v, q = solve(w)
        if best(q[w['start']]) != root_label:
            edge = edges[w['start']]; edge['A'], edge['B'] = edge['B'], edge['A']
            v, q = solve(w)
        witness, meaningful = optimal_witness(w, q)
        if len(meaningful)-1 < min(2, h-1):
            continue
        # Both predicate truth values must be possible in this same world.
        values = {w['payoffs'][s] for s in reachable(w, w['start'])}
        if not (min(values) < 4 <= max(values)):
            continue
        route_rng = rng_for(seed, h, attempt, 'route')
        for _ in range(10000):
            route = [route_rng.choice(('A', 'B')) for _ in range(h)]
            if (rollout(w, route)[1] >= 4) == route_truth:
                break
        else:
            raise RuntimeError('Could not sample a balanced route')
        w['layers'] = [sorted(layer) for layer in layers]
        return dict(id=f'{seed}_h{h}', seed=seed, horizon=h, world=w, route=route,
            route_truth=route_truth, root_q=q[w['start']], root_answer=root_label,
            witness=witness, consequential_layers=meaningful, attempts=attempt,
            route_terminal=rollout(w, route)[0], route_payoff=rollout(w, route)[1])
    raise RuntimeError('Generation exhausted')


def make_bank():
    items = []
    for h in HORIZONS:
        # Orthogonal balance: each (root optimum, route truth) combination twice.
        labels = [(a, t) for a in ('A', 'B') for t in (False, True) for _ in range(2)]
        rng_for('e118-labels', h).shuffle(labels)
        for seed, (a, t) in zip(SEEDS, labels):
            items.append(generate(seed, h, a, t))
    controls = [dict(item_id=i['id'], task='readout') for i in items if i['horizon'] == 1]
    main = [dict(item_id=i['id'], task=t) for i in items for t in TASKS]
    rng_for('e118-order').shuffle(main)
    return dict(schema=1, seeds=SEEDS, horizons=HORIZONS, items=items, schedule=controls+main)


def truth(item, task):
    if task in ('choice', 'readout'):
        return item['root_answer']
    yes = 'A' if task == 'predict_yes_a' else 'B'
    return yes if item['route_truth'] else ('B' if yes == 'A' else 'A')


def question(item, task):
    if task == 'readout':
        state = {'exact_maximum_final_payoff_after_first_action': item['root_q']}
        instruction = 'Choose the first action with the larger exact maximum final payoff in the supplied table.'
        choices = dict(A='Choose action A.', B='Choose action B.')
    else:
        state = render(item['world'])
        if task == 'choice':
            instruction = ('Choose the first action allowing the largest achievable final payoff, '
                           'assuming all later actions are chosen optimally. Use the supplied complete rules.')
            choices = dict(A='Choose A as the first action.', B='Choose B as the first action.')
        elif task in TASKS:
            yes, no = ('A', 'B') if task == 'predict_yes_a' else ('B', 'A')
            state['prescribed_actions'] = item['route']
            instruction = ('Follow exactly the prescribed_actions from start; do not optimize or change them. '
                           f'Is the final payoff at least 4? Choose {yes} for yes and {no} for no.')
            choices = {yes: 'Yes: final payoff is at least 4.', no: 'No: final payoff is below 4.'}
        else:
            raise ValueError(task)
    return dict(state=state, question=dict(type='choice', instructions=instruction, criteria=choices))


def request_body(config, item, task):
    c, common = CONFIGS[config], question(item, task)
    if config == 'jev':
        return {'model': c['model'], 'state': common['state'], 'questions': {'answer': common['question']}}
    return {'model': c['model'], 'messages': [
        {'role': 'system', 'content': 'Use only the supplied state and question. Return a JSON object with a single choice key whose value is A or B.'},
        {'role': 'user', 'content': canonical(common)}],
        'max_tokens': 8192, 'reasoning': {'effort': c['effort'], 'exclude': False},
        'provider': {'only': [c['slug']], 'ignore': c['ignore'], 'allow_fallbacks': False,
            'require_parameters': True, 'max_price': {'prompt': c['prompt_max'], 'completion': c['completion_max']}},
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'binary_choice', 'strict': True,
            'schema': {'type': 'object', 'properties': {'choice': {'type': 'string', 'enum': ['A', 'B']}},
                       'required': ['choice'], 'additionalProperties': False}}}}


def reservation(config, body):
    if config == 'jev':
        return .005
    c = CONFIGS[config]
    return (len(canonical(body).encode()) + 2048) * c['input_price'] + 8192 * c['output_price']


def parse_choice(config, result):
    c = CONFIGS[config]
    if result.get('model') not in (c['model'], c['canonical']):
        raise ValueError('unexpected_model')
    if result.get('provider') != c['provider']:
        raise ValueError('unexpected_provider')
    if config == 'jev':
        choice = result.get('answers', {}).get('answer', {}).get('choice')
    else:
        entry = result.get('choices', [{}])[0]
        if entry.get('finish_reason') != 'stop':
            raise ValueError('finish_reason_' + str(entry.get('finish_reason')))
        content = entry.get('message', {}).get('content')
        try:
            answer = json.loads(content)
        except (TypeError, ValueError):
            raise ValueError('invalid_json') from None
        if not isinstance(answer, dict) or set(answer) != {'choice'}:
            raise ValueError('invalid_schema')
        choice = answer['choice']
    if choice not in ('A', 'B'):
        raise ValueError('invalid_choice')
    return choice


def verify_bank(bank):
    checks = 0
    for item in bank['items']:
        w = item['world']; v, q = solve(w)
        for layer in w['layers'][:-1]:
            for s in layer:
                assert v[s] == max(w['payoffs'][x] for x in reachable(w, s))
                checks += 1
        assert q[w['start']] == item['root_q']
        assert best(q[w['start']]) == item['root_answer']
        assert rollout(w, item['witness'])[1] == v[w['start']]
        assert rollout(w, item['route']) == (item['route_terminal'], item['route_payoff'])
        assert (item['route_payoff'] >= 4) == item['route_truth']
        assert truth(item, 'predict_yes_a') != truth(item, 'predict_yes_b')
        assert len(item['consequential_layers']) - 1 >= min(2, item['horizon']-1)
        assert question(item, 'predict_yes_a')['state'] == question(item, 'predict_yes_b')['state']
        assert 'root_q' not in question(item, 'choice')['state']
    for h in HORIZONS:
        items = [i for i in bank['items'] if i['horizon'] == h]
        assert len(items) == 8
        for a in ('A', 'B'):
            for t in (False, True):
                assert sum(i['root_answer'] == a and i['route_truth'] == t for i in items) == 2
    expected = {(i['id'], t) for i in bank['items'] for t in TASKS}
    expected |= {(i['id'], 'readout') for i in bank['items'] if i['horizon'] == 1}
    assert len(bank['schedule']) == 104
    assert {(c['item_id'], c['task']) for c in bank['schedule']} == expected
    return dict(passed=True, items=32, calls_per_configuration=104, forward_value_checks=checks,
                generation_attempts=sum(i['attempts'] for i in bank['items']))
