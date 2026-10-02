"""Fresh-process battle episodes, complete trace retention, no state edits."""
from collections import Counter
import time
import uuid

import numpy as np
import torch

from .battle_search import baseline_choice, boundary, choices_for, finish, outcome
from .engine import ROOT, Headless
from .ppo import encode, padded
from .trace import Trace, digest


def reward_for(result):
    if result['status'] == 'clear':
        return 1 + .25 * result['hp'] / max(1, result['max_hp'])
    if result['status'] == 'defeat':
        return -1.
    raise ValueError('Censored episode has no training reward')


def episode(frozen, manifest, label, model=None, sample_seed=None, expected=None,
            policy=None, seconds=30, checkpoint=None):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid, {**manifest, 'scope': manifest.get('experiment', 'E125')+'_battle',
                  'label': label, 'case': frozen['case'], 'sample_seed': sample_seed,
                  'restore_checkpoint': checkpoint})
    started = time.monotonic(); deadline = started + seconds
    result = dict(case=frozen['case'], label=label, run_id=uid, status='error', steps=0,
                  entry_verified=False, replay_seconds=0., plan=[], inference_seconds=0.,
                  illegal_actions=0, decisions=Counter(),
                  restore_mode='research_checkpoint' if checkpoint else 'full_prefix')
    engine = None; state = {}; data = []; previous = frozen['previous']
    rng = np.random.default_rng(sample_seed)
    def send(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Episode time cap')
        engine.timeout = min(10, remaining)
        return engine.send(command)
    try:
        if digest(frozen['prefix']) != frozen['prefix_hash']:
            raise ValueError('Changed canonical reset prefix')
        engine = Headless(trace.directory, timeout=10, resource_decisions=True)
        if checkpoint:
            from .research_restore import restore_entry
            state = restore_entry(send, frozen, checkpoint, manifest)
        else:
            for cmd in frozen['prefix']:
                state = send(cmd)
        result['replay_seconds'] = time.monotonic() - started
        if digest(state) != frozen['entry_hash']:
            raise ValueError('Reset entry mismatch')
        result['entry_verified'] = True
        for step in range(121):
            if boundary(state):
                result.update(outcome(state))
                if expected is not None and step != len(expected):
                    raise ValueError('Verification terminal length mismatch')
                break
            if step == 120:
                result['status'] = 'action_cap'; break
            choices = choices_for(state)
            encoded = encode(state, choices, previous)
            before = digest(state)
            payload = dict(before=before, candidates=choices)
            if expected is not None:
                if step >= len(expected) or before != expected[step]['before']:
                    raise ValueError('Verification before-state mismatch')
                chosen = next(c for c in choices if c['action'] == expected[step]['action'])
            elif policy is not None:
                chosen, extra = policy(state, choices, previous, result['plan'])
                payload.update(extra)
            elif model is None:
                chosen = baseline_choice(state, previous)
            else:
                clock = time.monotonic()
                with torch.inference_mode():
                    dist, v = model(*padded([encoded]))
                    probs = dist.probs[0].numpy().astype(np.float64)
                    probs /= probs.sum()
                    index = int(rng.choice(len(choices), p=probs)) if sample_seed is not None else int(np.argmax(probs))
                    lp, value = dist.logits[0, index].item(), v[0].item()
                result['inference_seconds'] += time.monotonic() - clock
                chosen = choices[index]
                data.append(dict(encoded=encoded, index=index, logprob=lp, value=value))
                payload.update(probabilities=probs.tolist(), index=index, old_logprob=lp, value=value)
            if chosen['action'] not in [c['action'] for c in choices]:
                result['illegal_actions'] += 1
                raise ValueError('Illegal action')
            payload['chosen'] = chosen; trace.write('decision', payload)
            result['decisions'][state['decision']] += 1
            state = send(chosen['action'])
            after = digest(state)
            if expected is not None and after != expected[step]['after']:
                raise ValueError('Verification after-state mismatch')
            result['plan'].append(dict(before=before, action=chosen['action'], after=after))
            result['steps'] += 1; previous = chosen
        result['final_hash'] = digest(state)
    except TimeoutError as exc:
        result.update(status='timeout', error=str(exc))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    result['transition_hash'] = digest(result['plan'])
    finish(trace, result, engine, started)
    if result['status'] in ('clear', 'defeat'):
        result['reward'] = reward_for(result)
    return result, data
