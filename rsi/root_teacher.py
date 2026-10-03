"""Bounded repeated root-action comparisons; no gradients or learned dynamics."""
from collections import Counter
import json
import time
import uuid

import numpy as np
import torch

from .battle_search import finish
from .checkpoints import file_hash, wire_pairs
from .curriculum import FightBoundary, cautious_macro
from .engine import ROOT, Headless
from .phase_rl import phase_encode
from .ppo import padded
from .ppo_actions import complete_baseline
from .resources import require_resource_interface
from .run_env import legal_choices, run_outcome
from .trace import Trace, digest


def probabilities(model, state, choices, previous):
    with torch.inference_mode():
        dist, _ = model(*padded([phase_encode(state, choices, previous, max_actions=4096)]))
        p = dist.probs[0].numpy().astype(np.float64)
    return p / p.sum()


def inverse_cdf(p, u):
    if not 0 <= u < 1 or not np.isfinite(p).all() or np.any(p < 0) or not np.isclose(sum(p), 1):
        raise ValueError('Invalid categorical draw')
    return min(len(p)-1, int(np.searchsorted(np.cumsum(p), u, side='right')))


def utility(r):
    if r['status'] not in ('clear', 'defeat'):
        raise ValueError('Censored outcomes cannot become action labels')
    return 1+.25*r['hp']/max(1, r['max_hp']) if r['status'] == 'clear' else -1.


def select_mean(groups):
    if not groups or any(not x for x in groups):
        raise ValueError('Missing candidate samples')
    # Candidate0 is actor; Python max preserves that tie preference.
    return max(range(len(groups)), key=lambda i: float(np.mean([utility(r) for r in groups[i]])))


def source_roots(record):
    """Last actual encounter plus its preceding preparation, with full provenance."""
    path = ROOT/record['trace_path']
    wire = path.with_name('wire.jsonl')
    if file_hash(path) != record['trace_sha256'] or file_hash(wire) != record['wire.jsonl_sha256']:
        raise ValueError('Changed source evidence')
    pairs = wire_pairs(wire)
    events = [x['data'] for line in path.read_text().splitlines()
              if (x := json.loads(line))['kind'] == 'decision']
    if len(events) != len(pairs)-1:
        raise ValueError('Decision/source alignment mismatch')
    for i, e in enumerate(events):
        if e['before'] != digest(pairs[i][1]) or e['chosen']['action'] != pairs[i+1][0]:
            raise ValueError('Source context mismatch')
    tracker, last_exit, latest = FightBoundary(), 0, None
    for i, (_, state) in enumerate(pairs):
        started = tracker.started
        end = tracker.observe(state)
        if state['decision'] == 'combat_play' and not started:
            latest = (i, last_exit, state.get('context', {}).get('room_type'))
        if end:
            if end == 'defeat' or state['decision'] == 'game_over':
                break
            last_exit, tracker = i, FightBoundary()
    if latest is None:
        raise ValueError('No natural combat in selected source')
    battle, prepare, room = latest
    out = []
    for mode, offset in [('combat', battle), ('prepare', prepare)]:
        state = pairs[offset][1]
        prefix = [c for c, _ in pairs[:offset+1]]
        root = dict(case=record['case']+':'+mode, seed=record['seed'], character=record['character'],
            ascension=record['ascension'], mode=mode, reference_room_type=room,
            prefix=prefix, prefix_hash=digest(prefix), root_hash=digest(state),
            prefix_state_hashes=[digest(s) for _, s in pairs[:offset+1]],
            previous=events[offset-1]['chosen'] if offset else None,
            root_phase=state['decision'], source_trace_path=record['trace_path'],
            source_trace_sha256=record['trace_sha256'], root_context=state.get('context'))
        out.append((root, state))
    return out


def candidates(model, root, state):
    choices = legal_choices(state, {})
    p = probabilities(model, state, choices, root['previous'])
    greedy = int(p.argmax())
    planner = (complete_baseline(state, choices, root['previous'])
               if state['decision'] in ('combat_play', 'card_select') else cautious_macro(state))
    selected = [greedy]
    selected += [i for i, c in enumerate(choices) if c['action'] == planner['action']]
    selected += [i for i, c in enumerate(choices) if c['action']['action'] in ('end_turn', 'skip_card_reward')]
    selected += sorted(range(len(choices)), key=lambda i: (-p[i], i))
    selected = list(dict.fromkeys(selected))[:4]
    return dict(choices=choices, probabilities=p.tolist(), selected_indices=selected,
                actions=[choices[i]['action'] for i in selected], omitted=len(choices)-len(selected))


def rollout(root, manifest, model, label, *, first_action=None, sample_seed=None,
            full=False, expected=None, seconds=30):
    trace = Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),
        {**manifest, 'scope': 'E149_root_continuation', 'case': root['case'], 'label': label,
         'first_action': first_action, 'sample_seed': sample_seed, 'full': full,
         'prefix_hash': root['prefix_hash'], 'root_hash': root['root_hash']})
    start = time.monotonic()
    deadline = start+seconds
    r = dict(case=root['case'], seed=root['seed'], label=label, mode=root['mode'],
        ascension=root['ascension'], status='error', steps=0, plan=[], scenes=Counter(),
        entry_verified=False, restore_mode='full_prefix', sample_seed=sample_seed,
        first_action=first_action, full=full, acts_seen=[], network_calls=0)
    engine, state, previous, history = None, {}, root['previous'], {}
    tracker, acts = FightBoundary(), set()
    rng = np.random.default_rng(sample_seed)
    limit = 2400 if full else 300

    def send(command):
        left = deadline-time.monotonic()
        if left <= 0:
            raise TimeoutError('Root continuation time cap')
        engine.timeout = min(15, left)
        return engine.send(command)

    try:
        if digest(root['prefix']) != root['prefix_hash'] or len(root['prefix']) != len(root['prefix_state_hashes']):
            raise ValueError('Invalid root prefix')
        engine = Headless(trace.directory, timeout=min(15, seconds), resource_decisions=True)
        for command, expected_hash in zip(root['prefix'], root['prefix_state_hashes']):
            state = send(command)
            if digest(state) != expected_hash:
                raise ValueError('Restored prefix response mismatch')
        if digest(state) != root['root_hash']:
            raise ValueError('Root identity mismatch')
        require_resource_interface(state)
        r.update(entry_verified=True, restore_seconds=time.monotonic()-start,
                 restore_commands=len(root['prefix']), entry_potions=len(state.get('player', {}).get('potions', [])))
        for step in range(limit+1):
            context = state.get('context') or {}
            if context.get('act'):
                acts.add(context['act'])
            end = run_outcome(state) if full else tracker.observe(state)
            if end:
                if not full and end == 'clear' and not tracker.started:
                    raise ValueError('Unplayed encounter cannot be a win')
                if expected is not None and step != len(expected):
                    raise ValueError('Replay length mismatch')
                r['status'] = end
                break
            if step == limit:
                r['status'] = 'action_cap'
                break
            choices = legal_choices(state, history)
            before, extra = digest(state), {}
            if expected is not None:
                if step >= len(expected) or before != expected[step]['before']:
                    raise ValueError('Replay before-state mismatch')
                action = expected[step]['action']
            elif step == 0 and first_action is not None:
                action = first_action
                extra['forced_root'] = True
            else:
                p = probabilities(model, state, choices, previous)
                u = None if sample_seed is None else float(rng.random())
                index = int(p.argmax()) if u is None else inverse_cdf(p, u)
                action = choices[index]['action']
                extra = dict(probabilities=p.tolist(), uniform=u, index=index)
                r['network_calls'] += 1
            chosen = next((c for c in choices if c['action'] == action), None)
            if chosen is None:
                raise ValueError('Action not legal in fresh state')
            trace.write('decision', dict(before=before, candidates=choices, chosen=chosen, **extra))
            if state['decision'] == 'map_select':
                history['removed_here'] = False
            if action['action'] == 'remove_card':
                history['removed_here'] = True
            r['scenes'][state['decision']] += 1
            state = send(action)
            after = digest(state)
            if expected is not None and after != expected[step]['after']:
                raise ValueError('Replay after-state mismatch')
            r['plan'].append(dict(before=before, action=action, after=after))
            r['steps'] += 1
            previous = chosen
    except TimeoutError as exc:
        r.update(status='timeout', error=str(exc))
    except Exception as exc:
        r.update(status='error', error=f'{type(exc).__name__}: {exc}')
    p = state.get('player') or {}
    r.update(hp=p.get('hp', 0), max_hp=p.get('max_hp', 1), gold=p.get('gold', 0),
        potions=[x.get('id', x.get('name')) for x in p.get('potions', [])],
        deck_hash=digest(p.get('deck')), actual_room_type=tracker.room_type,
        final_hash=digest(state), transition_hash=digest(r['plan']), acts_seen=sorted(acts))
    finish(trace, r, engine, start)
    if not full and r['status'] in ('clear', 'defeat'):
        r['utility'] = utility(r)
    return r
