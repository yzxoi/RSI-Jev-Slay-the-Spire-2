"""Natural encounter curricula; reward decisions belong to the next fight."""
from collections import Counter
import time
import uuid

from .battle_search import boundary, finish
from .checkpoints import file_hash, wire_pairs
from .engine import ROOT, Headless
from .full import fixed_macro
from .phase_rl import controller
from .run_env import legal_choices
from .trace import Trace, digest

ROOMS = ('Monster', 'Elite', 'Boss')


def cautious_macro(state):
    choices = [c for c in legal_choices(state, {})
               if c['action']['action'] not in ('use_potion', 'discard_potion')]
    if state['decision'] == 'potion_reward':
        action = 'claim_potion_reward' if state.get('can_claim') else 'skip_potion_reward'
        return next(c for c in choices if c['action']['action'] == action)
    return fixed_macro(state, choices, cautious_route=True)


class FightBoundary:
    def __init__(self):
        self.started = False
        self.room_type = None
        self.act = None

    def observe(self, state):
        if state['decision'] == 'game_over':
            return 'clear' if state.get('victory') else 'defeat'
        if state['decision'] == 'combat_play':
            if not self.started:
                self.room_type = state.get('context', {}).get('room_type')
                self.act = state.get('context', {}).get('act')
            self.started = True
            return None
        # An initial reward menu is preparation, not proof of a new battle win.
        return boundary(state) if self.started else None


def roots(record, entries=None, *, wanted=ROOMS):
    """First natural encounter of each requested class, no outcome filtering."""
    path = ROOT / record['trace_path']
    wire = path.with_name('wire.jsonl')
    if file_hash(path) != record['trace_sha256'] or file_hash(wire) != record['wire.jsonl_sha256']:
        raise ValueError('Changed curriculum source trace')
    pairs = wire_pairs(wire)
    import json
    events = [x['data'] for line in path.read_text().splitlines()
              if (x := json.loads(line))['kind'] in ('decision', 'selected')]
    if len(events) != len(pairs)-1:
        raise ValueError('Source action alignment changed')
    choices = [e.get('chosen', e.get('choice')) for e in events]
    for i, (e, choice) in enumerate(zip(events, choices)):
        if e['before'] != digest(pairs[i][1]) or choice['action'] != pairs[i+1][0]:
            raise ValueError('Source previous-action context mismatch')
    selected, seen, last_exit = [], set(), 0
    tracker = FightBoundary()
    for i, (_, state) in enumerate(pairs):
        was_started = tracker.started
        result = tracker.observe(state)
        if state['decision'] == 'combat_play' and not was_started:
            room = state.get('context', {}).get('room_type')
            if room in wanted and room not in seen:
                seen.add(room)
                for mode, start in (('combat', i), ('prepare', last_exit)):
                    root_state = pairs[start][1]
                    prefix = [c for c, _ in pairs[:start+1]]
                    selected.append(dict(case=f"{record['case']}:{room}:{mode}",
                        seed=record['seed'], split=record['split'], character=record['character'],
                        ascension=record['ascension'], reference_room_type=room, mode=mode,
                        root_phase=root_state['decision'], root_act=root_state.get('context', {}).get('act'),
                        reference_act=state.get('context', {}).get('act'),
                        root_hash=digest(root_state), prefix=prefix, prefix_hash=digest(prefix),
                        previous=choices[start-1] if start else None,
                        source_case=record['case'], source_trace_path=record['trace_path'],
                        source_trace_sha256=record['trace_sha256'], source_wire_sha256=record['wire.jsonl_sha256']))
        if result:
            if result == 'defeat' or state['decision'] == 'game_over':
                break
            last_exit = i
            tracker = FightBoundary()
    return selected


def episode(root, manifest, label, model=None, sample_seed=None, expected=None, seconds=60):
    trace = Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),
        {**manifest, 'scope': 'E153_real_encounter', 'case': root['case'], 'mode': root['mode'],
         'label': label, 'sample_seed': sample_seed, 'prefix_hash': root['prefix_hash']})
    started = time.monotonic()
    deadline = started+seconds
    r = dict(case=root['case'], seed=root['seed'], ascension=root['ascension'], mode=root['mode'],
        reference_room_type=root['reference_room_type'], root_phase=root['root_phase'],
        label=label, status='error', steps=0, plan=[], scenes=Counter(),
        network_calls=0, illegal_actions=0, restore_mode='verified_full_prefix', entry_verified=False)
    engine, state, trajectory = None, {}, []
    tracker, history, previous = FightBoundary(), {}, root['previous']
    choose = controller(model, sample_seed, trajectory if sample_seed is not None else None) if model is not None else None

    def send(command):
        left = deadline-time.monotonic()
        if left <= 0:
            raise TimeoutError('Curriculum episode budget')
        engine.timeout = min(15, left)
        return engine.send(command)

    try:
        if digest(root['prefix']) != root['prefix_hash']:
            raise ValueError('Changed root prefix')
        engine = Headless(trace.directory, timeout=min(15, seconds), resource_decisions=True)
        for command in root['prefix']:
            state = send(command)
        if digest(state) != root['root_hash']:
            raise ValueError('Natural root restore mismatch')
        r.update(entry_verified=True, restore_seconds=time.monotonic()-started)
        for step in range(301):
            terminal = tracker.observe(state)
            if terminal:
                if terminal == 'clear' and not tracker.started:
                    raise ValueError('Cannot label preparation-only path a combat win')
                if expected is not None and step != len(expected):
                    raise ValueError('Replay terminal length differs')
                r['status'] = terminal
                break
            if step == 300:
                r['status'] = 'action_cap'
                break
            choices = legal_choices(state, history)
            before = digest(state)
            extra = {}
            if expected is not None:
                if step >= len(expected) or before != expected[step]['before']:
                    raise ValueError('Replay before-state differs')
                selected = next(c for c in choices if c['action'] == expected[step]['action'])
            elif choose is not None:
                selected, extra = choose(state, choices, previous)
                r['network_calls'] += 1
            else:
                from .ppo_actions import complete_baseline
                selected = complete_baseline(state, choices, previous) if tracker.started or state['decision'] == 'card_select' else cautious_macro(state)
            if selected['action'] not in [c['action'] for c in choices]:
                r['illegal_actions'] += 1
                raise ValueError('Illegal curriculum action')
            trace.write('decision', dict(before=before, candidates=choices, chosen=selected, **extra))
            if state['decision'] == 'map_select':
                history['removed_here'] = False
            if selected['action']['action'] == 'remove_card':
                history['removed_here'] = True
            r['scenes'][state['decision']] += 1
            state = send(selected['action'])
            after = digest(state)
            if expected is not None and after != expected[step]['after']:
                raise ValueError('Replay after-state differs')
            r['plan'].append(dict(before=before, action=selected['action'], after=after))
            r['steps'] += 1
            previous = selected
    except TimeoutError as e:
        r.update(status='timeout', error=str(e))
    except Exception as e:
        r.update(status='error', error=f'{type(e).__name__}: {e}')
    p = state.get('player') or {}
    r.update(actual_room_type=tracker.room_type, actual_act=tracker.act, battle_started=tracker.started,
        hp=p.get('hp', 0), max_hp=p.get('max_hp', 1), gold=p.get('gold', 0),
        potions=[x.get('id', x.get('name')) for x in p.get('potions', [])],
        deck_hash=digest(p.get('deck')), final_hash=digest(state), transition_hash=digest(r['plan']))
    finish(trace, r, engine, started)
    if r['status'] in ('clear', 'defeat'):
        r['reward'] = 1.+.25*r['hp']/max(1, r['max_hp']) if r['status'] == 'clear' else -1.
    return r, trajectory
