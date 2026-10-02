"""Explicit, bounded recovery of pre-policy loader stalls and PPO shuffle state."""
import json
import math
import time
from pathlib import Path

import numpy as np

from .battle_search import compact
from .checkpoints import file_hash
from .engine import ROOT
from .ppo import HP
from .ppo_env import episode

PROTOCOL = 'e137-predecision-load-once-and-exact-resume-v1'


def retry_eligible(result, data, checkpoint):
    if (not checkpoint or data or result.get('status') != 'timeout'
            or result.get('steps') != 0 or result.get('entry_verified') is not False
            or result.get('decisions') or 'reward' in result
            or result.get('restore_mode') != 'research_checkpoint'
            or result.get('error') != 'Headless response deadline exceeded'):
        return False
    path = ROOT/result['trace_path']
    for name, key in [('decisions.jsonl', 'trace_sha256'), ('wire.jsonl', 'wire.jsonl_sha256'),
                      ('engine.stderr.log', 'engine.stderr.log_sha256')]:
        if file_hash(path.with_name(name)) != result.get(key):
            return False
    rows = [json.loads(line) for line in path.with_name('wire.jsonl').read_text().splitlines()]
    return (len(rows) == 2 and rows[0]['kind'] == 'state' and rows[0]['data'].get('type') == 'ready'
            and rows[1]['kind'] == 'command'
            and rows[1]['data'] == {'cmd': 'load_save', 'path': str(ROOT/checkpoint['path'])})


def training_episode(frozen, manifest, label, *, seconds=30, **kwargs):
    started = time.monotonic()
    first, data = episode(frozen, manifest, label, seconds=seconds, **kwargs)
    remaining = seconds - (time.monotonic() - started)
    # episode() closes and waits for its disposable process before returning.
    if remaining <= 0 or not retry_eligible(first, data, kwargs.get('checkpoint')):
        return first, data
    second, data = episode(frozen, {**manifest, 'reset_retry_source': first['run_id'],
                                   'reset_retry_protocol': PROTOCOL}, label+':reset_retry:1',
                           seconds=remaining, **kwargs)
    second['reset_retry_attempts'] = [compact(first)]
    second['successful_attempt_seconds'] = second['seconds']
    second['seconds'] = time.monotonic()-started
    second['replay_seconds'] += first['seconds']
    return second, data


def shuffle_rng(learner, updates):
    """Reconstruct every permutation call, including a KL-stop epoch's first call."""
    rng = np.random.default_rng(learner)
    for index, row in enumerate(updates, 1):
        if row['update'] != index or row.get('optimizer_skipped') or 'optimization' not in row:
            raise ValueError('Noncontiguous completed optimizer history')
        opt = row['optimization']
        batches = math.ceil(opt['transitions']/HP['minibatch'])
        epochs = opt['minibatches']//batches+1 if opt['kl_early_stop'] else HP['epochs']
        if not 1 <= epochs <= HP['epochs']:
            raise ValueError('Impossible PPO epoch history')
        for _ in range(epochs):
            rng.permutation(opt['transitions'])
    return rng
