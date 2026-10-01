"""E120 opt-in battle-plan search against independent official-engine processes."""
from collections import Counter
import hashlib
import math
import random
import time
import uuid

from .engine import ROOT, Headless
from .full import macro_candidates, fixed_macro
from .mcts import Flat, UCT
from .policy import combat_candidates
from .potions import with_potions
from .resources import require_resource_interface
from .teacher import select, terminal
from .trace import Trace, digest

CONTROL = dict(mode='legacy', loss_price=1.5, potions='early')
LIMITS = dict(simulations=24, search_seconds=120, probe_seconds=15,
              probe_actions=120, fixture_seconds=90, fixture_actions=700,
              rollout_epsilon=.1, workers=2)


def choices_for(state):
    if state['decision'] == 'combat_play':
        return with_potions(state, combat_candidates(state))
    return macro_candidates(state, resource_decisions=True)


def baseline_choice(state, previous=None):
    return select(state, CONTROL, previous)[0]


def macro_choice(state):
    choices = [c for c in choices_for(state)
               if c['action']['action'] not in ('use_potion', 'discard_potion')]
    if state['decision'] == 'map_select':
        elites = [c for c in choices if c['details']['type'] == 'Elite']
        if elites:
            return elites[0]
    if state['decision'] == 'potion_reward':
        name = 'claim_potion_reward' if state['can_claim'] else 'skip_potion_reward'
        return next(c for c in choices if c['action']['action'] == name)
    return fixed_macro(state, choices)


def boundary(state):
    return {'boss_clear': 'clear', 'boss_defeat': 'defeat'}.get(terminal(state))


def outcome(state):
    player = state.get('player', {})
    return {'status': boundary(state), 'hp': player.get('hp', 0),
            'max_hp': player.get('max_hp'),
            'potions': [p.get('id', p['name']) for p in player.get('potions', [])]}


def rank(result, potion_weight=4):
    if result['status'] not in ('clear', 'defeat'):
        raise ValueError('Incomplete probes have no terminal rank')
    return (int(result['status'] == 'clear'),
            result['hp'] + potion_weight * len(result['potions'])
            if result['status'] == 'clear' else 0,
            -result['steps'] if result['status'] == 'clear' else 0)


def utility(result, fixture):
    if result['status'] not in ('clear', 'defeat'):
        raise ValueError('Incomplete probes have no terminal utility')
    if result['status'] == 'defeat':
        return 0.
    denom = max(1, fixture['max_hp'] + 4 * fixture['potion_capacity'])
    return .5 + .5 * min(1., (result['hp'] + 4 * len(result['potions'])) / denom)


def finish(trace, result, engine, started):
    if engine:
        engine.close()
    stderr = trace.directory / 'engine.stderr.log'
    if stderr.exists() and 'forcing game_over' in stderr.read_text():
        result.update(status='error', error='Engine forced game_over after a stall')
    result['seconds'] = time.monotonic() - started
    for filename in ('wire.jsonl', 'engine.stderr.log'):
        path = trace.directory / filename
        result[filename + '_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    trace.write('summary', {k: v for k, v in result.items() if k != 'plan'})
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()


def fixture(config, manifest):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, 'scope': 'E120_fixture', 'config': config, 'limits': LIMITS})
    result = {**config, 'status': 'error', 'run_id': uid, 'prefix': [], 'steps': 0}
    engine, state, previous = None, {}, None
    started = time.monotonic()
    deadline = started + LIMITS['fixture_seconds']
    prefix = [{'cmd': 'start_run', **{k: config[k] for k in ('character', 'seed', 'ascension')}}]
    in_battle = False
    try:
        engine = Headless(trace.directory, timeout=15, resource_decisions=True)
        state = engine.send(prefix[0])
        require_resource_interface(state)
        for step in range(LIMITS['fixture_actions'] + 1):
            context = state.get('context') or {}
            if state['decision'] == 'game_over':
                result['status'] = 'defeat_before_entry'
                break
            if state['decision'] == 'combat_play':
                in_battle = True
                if context.get('room_type') in ('Elite', 'Boss'):
                    trace.write('entry', state)
                    result.update(status='ready', entry_hash=digest(state), previous=previous,
                                  floor=context.get('floor'), room_type=context['room_type'],
                                  hp=state['player']['hp'], max_hp=state['player']['max_hp'],
                                  potion_capacity=state['player']['potion_capacity'],
                                  enemies=[e['name'] for e in state['enemies']],
                                  entry_potions=[p.get('id', p['name']) for p in state['player']['potions']])
                    break
            if context.get('act', 1) > 1:
                result['status'] = 'entry_not_found'
                break
            if step == LIMITS['fixture_actions'] or time.monotonic() >= deadline:
                result['status'] = 'fixture_cap'
                break
            if in_battle and boundary(state):
                in_battle = False
            chosen = baseline_choice(state, previous) if in_battle else macro_choice(state)
            if chosen['action'] not in [c['action'] for c in choices_for(state)]:
                raise ValueError('Fixture policy nominated an illegal action')
            trace.write('selected', {'before': digest(state), 'choice': chosen})
            engine.timeout = max(.01, min(15, deadline - time.monotonic()))
            state = engine.send(chosen['action'])
            prefix.append(chosen['action'])
            previous = chosen
            result['steps'] += 1
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    result.update(prefix=prefix, prefix_hash=digest(prefix), seconds=time.monotonic() - started)
    finish(trace, result, engine, started)
    return result


class TreePolicy:
    def __init__(self, tree, rng):
        self.tree, self.rng = tree, rng
        self.path = [tree.root]
        self.in_tree = True
        self.pending = None
        self.depth = 0

    def choose(self, state, choices, previous):
        if self.in_tree:
            if isinstance(self.tree, Flat):
                selected, child = self.tree.choose(digest(state), choices)
                self.in_tree = False
            else:
                selected, child, expanded = self.tree.choose(self.path[-1], digest(state), choices)
                self.in_tree = not expanded
            self.path.append(child)
            self.pending = child
            self.depth += 1
            return selected, 'tree'
        if self.rng.random() < LIMITS['rollout_epsilon']:
            return self.rng.choice(choices), 'rollout_random'
        return baseline_choice(state, previous), 'rollout_control'

    def observe(self, state):
        if self.pending is not None:
            self.pending.bind(digest(state))
            self.pending = None


def probe(frozen, manifest, label, policy=None, expected_plan=None, seconds=None):
    """Fresh process; checked history; exactly one bounded battle continuation."""
    uid = str(uuid.uuid4())
    budget = LIMITS['probe_seconds'] if seconds is None else seconds
    started = time.monotonic()
    deadline = started + budget
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, 'scope': 'E120_probe', 'label': label, 'case': frozen['case'],
                   'entry_hash': frozen['entry_hash'], 'prefix_hash': frozen['prefix_hash'],
                   'budget_seconds': budget, 'limits': LIMITS})
    result = {'label': label, 'run_id': uid, 'status': 'error', 'steps': 0,
              'entry_verified': False, 'replay_seconds': 0., 'replay_commands': 0,
              'sources': {}, 'selection_truncations': 0, 'last_combat_round': None, 'plan': []}
    engine, state = None, {}
    previous = frozen['previous']
    sources = Counter()

    def send(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Probe time budget exhausted')
        engine.timeout = min(15, remaining)
        return engine.send(command)

    try:
        prefix = frozen['prefix']
        if (not prefix or prefix[0]['cmd'] != 'start_run' or
                any(c['cmd'] != 'action' for c in prefix[1:]) or digest(prefix) != frozen['prefix_hash']):
            raise ValueError('Invalid canonical prefix')
        engine = Headless(trace.directory, timeout=max(.01, min(15, budget)), resource_decisions=True)
        for command in prefix:
            state = send(command)
            result['replay_commands'] += 1
        result['replay_seconds'] = time.monotonic() - started
        if digest(state) != frozen['entry_hash']:
            raise ValueError(f"Entry mismatch: expected {frozen['entry_hash']}, got {digest(state)}")
        require_resource_interface(state)
        result['entry_verified'] = True
        for step in range(LIMITS['probe_actions'] + 1):
            if boundary(state):
                result.update(outcome(state))
                if expected_plan is not None and step != len(expected_plan):
                    raise ValueError('Verification reached terminal at a different plan length')
                break
            if step == LIMITS['probe_actions']:
                result['status'] = 'action_cap'
                break
            choices = choices_for(state)
            if state['decision'] == 'combat_play':
                result['last_combat_round'] = state.get('round')
            if state['decision'] == 'card_select':
                n = len(state['cards'])
                total = sum(math.comb(n, k) for k in range(state.get('min_select', 1),
                            min(n, state.get('max_select', 1)) + 1))
                result['selection_truncations'] += int(total > len(choices))
            before_hash = digest(state)
            if expected_plan is not None:
                if step >= len(expected_plan) or expected_plan[step]['before'] != before_hash:
                    raise ValueError('Verification before-state or length mismatch')
                chosen = next((c for c in choices if c['action'] == expected_plan[step]['action']), None)
                source = 'independent_verification'
            elif policy:
                chosen, source = policy.choose(state, choices, previous)
            else:
                chosen, source = baseline_choice(state, previous), 'control'
            if chosen is None or chosen['action'] not in [c['action'] for c in choices]:
                raise ValueError('Illegal proposed action')
            trace.write('decision', {'before': before_hash, 'candidates': choices,
                                     'chosen': chosen, 'source': source})
            state = send(chosen['action'])
            after_hash = digest(state)
            result['plan'].append({'before': before_hash, 'action': chosen['action'], 'after': after_hash})
            result['steps'] += 1
            sources[source] += 1
            if expected_plan is not None and expected_plan[step]['after'] != after_hash:
                raise ValueError('Verification after-state mismatch')
            if policy:
                policy.observe(state)
            previous = chosen
        result['final_hash'] = digest(state)
    except TimeoutError as exc:
        result.update(status='timeout', error=str(exc))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    if not result['entry_verified']:
        result['replay_seconds'] = time.monotonic() - started
    result.update(sources=dict(sources), path_hash=digest([p['action'] for p in result['plan']]))
    finish(trace, result, engine, started)
    return result


def compact(result):
    return {k: v for k, v in result.items() if k != 'plan'}


def search(frozen, manifest, arm, control):
    started = time.monotonic()
    deadline = started + max(0, LIMITS['search_seconds'] - control['seconds'])
    seed = digest([frozen['case'], arm])
    tree = (Flat if arm == 'flat' else UCT)(random.Random(seed))
    best = control
    records, curves = [compact(control)], []
    paths = {control['path_hash']}
    status = 'complete'
    for index in range(1, LIMITS['simulations']):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            status = 'time_cap'
            break
        policy = TreePolicy(tree, random.Random(digest([seed, index])))
        result = probe(frozen, manifest, f'{arm}:{index}', policy=policy,
                       seconds=min(LIMITS['probe_seconds'], remaining))
        records.append(compact(result))
        paths.add(result['path_hash'])
        if result['status'] == 'error':
            status = 'invalid'
            break
        if result['status'] in ('clear', 'defeat'):
            tree.backup(policy.path, utility(result, frozen))
            if rank(result) > rank(best):
                best = result
        if len(records) in (8, 24):
            curves.append({'simulations': len(records),
                           'charged_seconds': control['seconds'] + time.monotonic() - started,
                           'incumbent': compact(best)})
    # Keep the best certified continuation when a budget expires (E115 gap).
    searched_seconds = time.monotonic() - started
    verification = None
    if status != 'invalid':
        verification = probe(frozen, manifest, f'{arm}:verification', expected_plan=best['plan'])
        if (verification['status'] != best['status'] or
                verification.get('final_hash') != best.get('final_hash') or
                verification['plan'] != best['plan']):
            status = 'invalid'
    return {'arm': arm, 'status': status, 'incumbent': compact(best),
            'verification': compact(verification) if verification else None,
            'charged_seconds': searched_seconds + control['seconds'],
            'probe_seconds': sum(r['seconds'] for r in records),
            'replay_seconds': sum(r['replay_seconds'] for r in records),
            'unique_action_paths': len(paths), 'simulations': len(records),
            'probe_statuses': dict(Counter(r['status'] for r in records)),
            'curve': curves, 'tree': tree.summary(), 'probes': records}
