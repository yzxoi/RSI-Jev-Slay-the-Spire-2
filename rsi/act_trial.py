"""E104 opt-in Act-1 harness using the existing Jev/legality/resource interface."""
from collections import Counter
import hashlib
import json
import time

from .engine import ROOT, Headless
from .end_turn_recheck import act1_clear, recheck_gate, review_payload
from .full import STRATEGY, macro_candidates
from .guard import filter_end_turn
from .jev import Budget, Jev
from .policy import combat_candidates, model_state
from .potions import with_potions
from .resources import inventory, require_resource_interface
from .trace import Trace, digest


class RunBudget:
    def __init__(self, session, config):
        self.local = Budget(config['max_model_attempts'], config['max_usd'], conservative_failures=True)
        self.session = session

    def acquire(self):
        self.local.acquire()
        try:
            self.session.acquire()
        except Exception:
            # No API attempt happened. Each local budget has a single writer.
            with self.local.lock:
                self.local.calls -= 1
                self.local.reserved -= self.local.reserve_usd
            raise

    def settle(self, usage):
        self.local.settle(usage)
        self.session.settle(usage)


def candidate_set(state, history):
    if state['decision'] == 'combat_play':
        legal = with_potions(state, combat_candidates(state))
        allowed, guard = filter_end_turn(state, legal)
        return legal, allowed, guard
    legal = macro_candidates(state, history, resource_decisions=True)
    return legal, legal, None


def decision_payload(state, history):
    payload = {'state': model_state(state), 'strategy': STRATEGY}
    if state['decision'] != 'combat_play':
        payload['previous_decision'] = history.get('previous')
    return payload


def advance_history(history, before, selected):
    if before['decision'] == 'map_select':
        history['removed_here'] = False
    if selected['action']['action'] == 'remove_card':
        history['removed_here'] = True
    if before['decision'] != 'card_select':
        history['previous'] = {'scene': before['decision'], 'choice': selected}


def episode(config, manifest, session):
    uid = config['run_id']
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, **config, 'experiment': 'E104', 'scope': 'fresh_start_act1'})
    budget = RunBudget(session, config)
    result = {**config, 'manifest': manifest, 'status': 'error', 'steps': 0,
              'triggers': 0, 'rechecks': 0, 'changed_choices': 0, 'repeated_end_turns': 0}
    engine = None
    state = {}
    history = {}
    started = time.monotonic()
    counts = Counter()
    scenes = Counter()
    phase_seconds = Counter()
    trajectory = []
    boss_entered = False
    last_hash = None
    unchanged = 0
    last_context = {}

    def progress():
        report = {**{k: result[k] for k in ('run_id', 'character', 'seed', 'arm', 'steps', 'triggers', 'rechecks')},
                  'status': 'running', 'context': state.get('context', last_context),
                  'decision': state.get('decision'), 'hp': state.get('player', {}).get('hp'),
                  'model_calls': budget.local.calls}
        temporary = trace.directory / 'progress.tmp'
        temporary.write_text(json.dumps(report) + '\n')
        temporary.replace(trace.directory / 'progress.json')

    def model_choose(jev, payload, allowed, phase):
        trace.write('request_phase', {'step': result['steps'], 'phase': phase, 'state_hash': digest(state)})
        choice, meta = jev.choose(payload, allowed, trace)
        phase_seconds[phase] += meta['seconds']
        return choice

    try:
        engine = Headless(trace.directory, resource_decisions=True)
        start_command = {'cmd': 'start_run', 'character': config['character'],
                         'ascension': config['ascension'], 'seed': config['seed']}
        state = engine.send(start_command)
        require_resource_interface(state)
        result['initial_state_hash'] = digest(state)
        trace.write('entry', {'state': state, 'state_hash': digest(state)})
        jev = Jev(budget)
        progress()
        for step in range(config['max_actions'] + 1):
            if state.get('context'):
                last_context = state['context']
            context = state.get('context') or {}
            if state.get('decision') == 'combat_play' and context.get('act') == 1 and context.get('room_type') == 'Boss':
                if not boss_entered:
                    result['boss_entry_hash'] = digest(state)
                    result['boss_name'] = (context.get('boss') or {}).get('name')
                    trace.write('boss_entry', {'state_hash': digest(state), 'context': context})
                boss_entered = True
            if state.get('decision') == 'game_over':
                result['status'] = 'unexpected_full_victory' if state.get('victory') else 'normal_defeat'
                break
            if act1_clear(state, boss_entered):
                result['status'] = 'act1_clear'
                break
            if step >= config['max_actions'] or time.monotonic() - started > config['max_seconds']:
                result['status'] = 'budget_exhausted'
                break
            h = digest(state)
            unchanged = unchanged + 1 if h == last_hash else 0
            last_hash = h
            if unchanged >= 5:
                raise RuntimeError('No state progress in six successive decisions')
            require_resource_interface(state)
            scenes[state['decision']] += 1
            legal, allowed, guard = candidate_set(state, history)
            trace.write('before', {'state': state, 'state_hash': h})
            trace.write('candidates', legal)
            trace.write('allowed_candidates', allowed)
            if guard is not None:
                trace.write('end_turn_guard', guard)
            source = 'jev'
            if state['decision'] == 'potion_reward' and state.get('can_claim'):
                selected = next(c for c in allowed if c['action']['action'] == 'claim_potion_reward')
                source = 'free_potion_claim'
            elif len(allowed) == 1:
                selected = allowed[0]
                source = 'only_legal_choice'
            else:
                payload = decision_payload(state, history)
                selected = model_choose(jev, payload, allowed, 'initial')
                gate = recheck_gate(state, selected, allowed)
                trace.write('recheck_gate', {'state_hash': h, 'proposal': selected, 'gate': gate})
                result['triggers'] += int(gate['eligible'])
                if config['arm'] == 'recheck' and gate['eligible']:
                    first = selected
                    selected = model_choose(jev, review_payload(payload, first, gate), allowed, 'recheck')
                    result['rechecks'] += 1
                    result['changed_choices'] += int(selected != first)
                    result['repeated_end_turns'] += int(selected['action']['action'] == 'end_turn')
                    trace.write('recheck_result', {'state_hash': h, 'initial': first, 'final': selected})
                    source = 'jev_recheck'
            if selected not in allowed:
                raise ValueError('Final action not in current allowed set')
            trace.write('selected', {'choice': selected, 'source': source})
            before = state
            state = engine.send(selected['action'])
            trace.write('after', {'state': state, 'state_hash': digest(state)})
            counts[selected['action']['action']] += 1
            trajectory.append([h, selected['action'], digest(state)])
            advance_history(history, before, selected)
            if selected['action']['action'] in ('use_potion', 'discard_potion', 'buy_potion', 'claim_potion_reward', 'skip_potion_reward'):
                trace.write('resource_transition', {'action': selected['action'], 'before': inventory(before),
                                                   'after': inventory(state), 'gold_before': before['player'].get('gold'),
                                                   'gold_after': state['player'].get('gold')})
            result['steps'] = step + 1
            progress()
    except Exception as exc:
        result['status'] = 'budget_exhausted' if 'budget exhausted' in str(exc).lower() else 'error'
        result['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', result['error'])
    finally:
        if engine:
            engine.close()
            log = (trace.directory / 'engine.stderr.log').read_bytes()
            result['engine_log_sha256'] = hashlib.sha256(log).hexdigest()
            if b'forcing game_over' in log:
                result['status'] = 'error'
                result['error'] = 'Upstream forced game_over; not a normal defeat'
    local = budget.local
    result.update(model_calls=local.calls, model_cost_usd=local.spent - local.estimated_usd,
                  unknown_model_calls=local.uncertain_calls, budgeted_usd=local.spent,
                  phase_seconds=dict(phase_seconds), final_hp=state.get('player', {}).get('hp'),
                  final_decision=state.get('decision'), floor=state.get('floor', last_context.get('floor')),
                  act=state.get('act', last_context.get('act')), seconds=round(time.monotonic() - started, 3),
                  action_counts=dict(counts), scene_counts=dict(scenes), trajectory_sha256=digest(trajectory),
                  final_state_hash=digest(state), boss_entered=boss_entered)
    wire = trace.directory / 'wire.jsonl'
    result['wire_sha256'] = hashlib.sha256(wire.read_bytes()).hexdigest() if wire.exists() else None
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()
    (trace.directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    (trace.directory / 'progress.json').write_text(json.dumps(result) + '\n')
    print(json.dumps({k: result.get(k) for k in ('run_id', 'character', 'seed', 'arm', 'status', 'floor', 'final_hp', 'model_calls', 'rechecks', 'error')}), flush=True)
    return result
