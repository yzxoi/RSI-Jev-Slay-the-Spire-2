"""Opt-in online policy portfolio, evaluated by independent real-game processes.

Heuristics nominate policies. Only observed engine outcomes rank them. Cached
continuations are bound to the complete command prefix AND observation, never a
seed lookup or a state-only transposition (hidden RNG may differ).
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time
import uuid

from .engine import ROOT, Headless
from .full import fixed_macro, macro_candidates
from .policy import combat_candidates
from .potions import with_potions
from .resources import require_resource_interface
from .teacher import select, terminal
from .trace import Trace, digest


POLICIES = {
    'control': dict(mode='legacy', loss_price=1.5, potions='early'),
    'reserve': dict(mode='legacy', loss_price=1.5, potions='none'),
    'defend': dict(mode='balanced', loss_price=3.0, potions='none'),
    'focus': dict(mode='focus_leader', loss_price=1.5, potions='selective'),
    'develop': dict(mode='scaling', loss_price=1.5, potions='turn3'),
    'draw': dict(mode='draw', loss_price=1.5, potions='early'),
}
LIMITS = dict(branch_seconds=15, branch_actions=150, batches=36,
              probes=180, search_seconds=360, episode_seconds=420,
              episode_actions=1500, branch_workers=3)
EMPTY_PREFIX = digest([])


def extend_prefix(key, command):
    return digest([key, command])


def prefix_digest(commands):
    key = EMPTY_PREFIX
    for command in commands:
        key = extend_prefix(key, command)
    return key


def position(state):
    context = state.get('context') or {}
    return (state.get('act', context.get('act', 1)),
            state.get('floor', context.get('floor', 0)))


def fresh_choices(state):
    if state.get('decision') == 'combat_play':
        return with_potions(state, combat_candidates(state))
    return macro_candidates(state, resource_decisions=True)


def legal_choice(state, command):
    return next((c for c in fresh_choices(state) if c['action'] == command), None)


def macro_choice(state):
    """Identical, deliberately fixed macro policy in both experimental arms."""
    choices = [c for c in fresh_choices(state)
               if c['action']['action'] not in ('use_potion', 'discard_potion')]
    if state['decision'] == 'potion_reward':
        wanted = 'claim_potion_reward' if state.get('can_claim') else 'skip_potion_reward'
        return next(c for c in choices if c['action']['action'] == wanted)
    return fixed_macro(state, choices)


def combat_boundary(state):
    status = terminal(state)
    return {'boss_clear': 'clear', 'boss_defeat': 'defeat'}.get(status)


def needs_refresh(before, choice, after):
    """New turn, generated/drawn cards and selection screens invalidate a plan."""
    if before.get('decision') != 'combat_play' or after.get('decision') != 'combat_play':
        return True
    if (position(before), before.get('round')) != (position(after), after.get('round')):
        return True
    remaining = Counter(c['id'] for c in before.get('hand', []))
    if choice['action']['action'] == 'play_card':
        index = choice['action']['args']['card_index']
        played = next(c for c in before['hand'] if c['index'] == index)
        remaining[played['id']] -= 1
    return bool(Counter(c['id'] for c in after.get('hand', [])) - remaining)


def outcome_rank(result):
    if result['status'] == 'clear':
        return (2, result['hp'] + 6 * result['potions_left'], -result['round'])
    if result['status'] == 'defeat':
        return (0, -result['enemy_hp'], result['round'])
    raise ValueError('Incomplete/error branches cannot be scored as game outcomes')


def close_trace(trace, result):
    for name, key in [('wire.jsonl', 'wire_sha256'), ('engine.stderr.log', 'stderr_sha256')]:
        path = trace.directory / name
        result[key] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()


def probe(prefix, entry, previous, mode, manifest, limits, timeout):
    """Replay canonical history, then run ONE policy to a genuine battle boundary."""
    started = time.monotonic()
    deadline = started + timeout
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, 'scope': 'speculative_battle', 'policy': mode,
                   'entry_hash': digest(entry), 'prefix_hash': prefix_digest(prefix),
                   'limits': limits, 'timeout': timeout})
    result = dict(run_id=uid, mode=mode, status='error', steps=0, entry_verified=False,
                  replay_seconds=0, replay_commands=0, entry_hash=digest(entry))
    engine = None
    state = {}
    path = []
    key = EMPTY_PREFIX
    last_combat = entry

    def send(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Branch time budget exhausted')
        engine.timeout = min(15, remaining)
        return engine.send(command)

    try:
        if not prefix or prefix[0].get('cmd') != 'start_run' or any(
                c.get('cmd') != 'action' for c in prefix[1:]):
            raise ValueError('Only a canonical start_run + action prefix is allowed')
        engine = Headless(trace.directory, timeout=min(15, timeout), resource_decisions=True)
        for command in prefix:
            state = send(command)
            key = extend_prefix(key, command)
            result['replay_commands'] += 1
        result['replay_seconds'] = time.monotonic() - started
        if digest(state) != digest(entry):
            result['actual_entry_hash'] = digest(state)
            raise ValueError('Replay entry mismatch')
        require_resource_interface(state)
        result['entry_verified'] = True
        trace.write('entry', {'state': state, 'prefix_hash': key})
        for step in range(limits['branch_actions'] + 1):
            boundary = combat_boundary(state)
            if boundary:
                result['status'] = boundary
                break
            if step == limits['branch_actions']:
                result['status'] = 'action_cap'
                break
            if state.get('decision') == 'combat_play':
                last_combat = state
            chosen, _, planning = select(state, POLICIES[mode], previous)
            command = chosen['action']
            fresh = legal_choice(state, command)
            if fresh is None:
                raise ValueError('Policy nominated an illegal action')
            before = digest(state)
            trace.write('before', {'state': state, 'state_hash': before, 'prefix_hash': key})
            trace.write('candidates', fresh_choices(state))
            trace.write('proposal', planning)
            trace.write('selected', fresh)
            state = send(command)
            after = digest(state)
            trace.write('after', {'state': state, 'state_hash': after})
            path.append(dict(prefix_hash=key, before=before, action=command, after=after,
                             source_trace=uid, mode=mode))
            key = extend_prefix(key, command)
            previous = chosen
            result['steps'] += 1
        result.update(hp=state.get('player', {}).get('hp', 0),
                      potions_left=len(state.get('player', {}).get('potions', [])),
                      enemy_hp=sum(e['hp'] for e in last_combat.get('enemies', [])),
                      round=last_combat.get('round', 0), final_hash=digest(state))
    except TimeoutError as exc:
        result.update(status='timeout', error=str(exc))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        if engine:
            engine.close()
            if 'forcing game_over' in (trace.directory / 'engine.stderr.log').read_text():
                result.update(status='error', error='Engine forced game_over after a stall')
    if not result['entry_verified']:
        result['replay_seconds'] = time.monotonic() - started
    result['seconds'] = time.monotonic() - started
    close_trace(trace, result)
    return result, path if result['status'] in ('clear', 'defeat') else []


class EngineSearch:
    def __init__(self, manifest, trace, limits=None):
        self.manifest = manifest
        self.trace = trace
        self.limits = dict(LIMITS if limits is None else limits)
        self.cache = {}
        self.active_mode = None
        self.refresh = True
        self.stats = Counter()
        self.probes = []
        self.search_seconds = 0.0

    def lookup(self, mode, prefix_key, state):
        return self.cache.get((mode, prefix_key, digest(state)))

    def remember(self, result, path):
        if result['status'] not in ('clear', 'defeat'):
            return
        for step in path:
            self.cache[(result['mode'], step['prefix_hash'], step['before'])] = {
                **step, 'outcome': result}

    def decide(self, state, prefix, key, previous, episode_deadline):
        """Return just one freshly legal choice, with its evidence if available."""
        nominations = {mode: select(state, policy, previous)[0]
                       for mode, policy in POLICIES.items()}
        control = nominations['control']
        active = self.lookup(self.active_mode, key, state)
        if active and not self.refresh:
            chosen = legal_choice(state, active['action'])
            if chosen is None:
                raise ValueError('Cached action not freshly legal')
            self.stats['verified_suffix_actions'] += 1
            return chosen, active, 'verified_suffix'
        if len({digest(c['action']) for c in nominations.values()}) == 1:
            self.stats['consensus_actions'] += 1
            return control, None, 'consensus'
        needed = [m for m in POLICIES if not self.lookup(m, key, state)]
        remaining = min(self.limits['search_seconds'] - self.search_seconds,
                        episode_deadline - time.monotonic() - 1)
        if (self.stats['batches'] >= self.limits['batches'] or
                self.stats['probes'] + len(needed) > self.limits['probes'] or remaining <= 0):
            self.stats['budget_fallbacks'] += 1
            self.active_mode = None
            return control, None, 'budget_control'
        self.stats['batches'] += 1
        self.stats['probes'] += len(needed)
        started = time.monotonic()
        # The timeout includes startup and complete prefix replay. Each queued
        # worker computes its remaining deadline when it actually begins.
        batch_deadline = started + remaining
        def run(mode):
            timeout = max(.01, min(self.limits['branch_seconds'], batch_deadline - time.monotonic()))
            return probe(prefix, state, previous, mode, self.manifest, self.limits, timeout)
        with ThreadPoolExecutor(max_workers=self.limits['branch_workers']) as pool:
            for result, path in pool.map(run, needed):
                self.probes.append(result)
                self.remember(result, path)
                self.stats[f"probe_{result['status']}"] += 1
        self.search_seconds += time.monotonic() - started
        available = [self.lookup(m, key, state) for m in POLICIES]
        available = [r for r in available if r is not None]
        self.trace.write('comparison', {
            'state_hash': digest(state), 'prefix_hash': key,
            'nominations': nominations, 'new_probes': [r['run_id'] for r in self.probes[-len(needed):]] if needed else [],
            'options': [{'mode': r['mode'], 'action': r['action'],
                         'outcome': r['outcome'], 'rank': outcome_rank(r['outcome'])} for r in available]})
        if not available:
            self.active_mode = None
            self.stats['unresolved_fallbacks'] += 1
            return control, None, 'unresolved_control'
        best = max(available, key=lambda r: outcome_rank(r['outcome']))
        chosen = legal_choice(state, best['action'])
        if chosen is None:
            raise ValueError('Evaluated action not freshly legal')
        self.active_mode = best['mode']
        self.refresh = False
        self.stats['selected_' + best['mode']] += 1
        self.stats['changed_control_action'] += chosen['action'] != control['action']
        return chosen, best, 'engine_comparison'

    def observe(self, before, chosen, after, evidence):
        if evidence:
            self.stats['predictions_checked'] += 1
            if digest(after) != evidence['after']:
                self.stats['prediction_mismatches'] += 1
                self.trace.write('prediction_mismatch', {
                    'expected': evidence['after'], 'actual': digest(after), 'evidence': evidence})
                self.cache.clear()
                self.active_mode = None
                self.refresh = True
                raise ValueError('Canonical transition differs from the verified branch')
        self.refresh = self.refresh or needs_refresh(before, chosen, after)

    def summary(self):
        return {**dict(self.stats), 'search_seconds': self.search_seconds,
                'prefix_seconds_sum': sum(p['replay_seconds'] for p in self.probes),
                'probe_seconds_sum': sum(p['seconds'] for p in self.probes),
                'probes': self.probes}
