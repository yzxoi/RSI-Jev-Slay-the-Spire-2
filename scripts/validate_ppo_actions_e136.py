#!/usr/bin/env python3
"""Resolve the frozen real selection failure with unchanged weights/randomness."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash, wire_pairs
from rsi.ppo_env import episode
from rsi.ppo_actions import complete_choices
from rsi.trace import digest
from rsi.training_bank import matched
from scripts.retrain_ppo_e133 import version, bank, load_model
from scripts.evaluate_battle_search_e120 import audit, write


def main(output):
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    v = {**version(), 'experiment': 'E136'}
    started = time.monotonic()
    source_path = ROOT/'experiments/E133/training-v1.json'
    source = json.loads(source_path.read_text())
    learner = next(r for r in source['learners'] if r['learner'] == 1702)
    old = next(r for r in learner['updates'][0]['episodes'] if r['case'] == 'train-113-b5')
    if old['status'] != 'error' or old['steps'] != 18 or not audit(source)['pass']:
        raise ValueError('Changed original error evidence')
    b = bank(v); f = next(f for f in b['fixtures'] if f['case'] == old['case'])
    pairs = wire_pairs((ROOT/old['trace_path']).with_name('wire.jsonl'))
    n = len(f['prefix']); before = pairs[n-1][1]; expected = []
    for action, after in pairs[n:]:
        expected.append(dict(before=digest(before), action=action, after=digest(after)))
        before = after
    if digest(expected) != old['transition_hash'] or len(expected) != 18:
        raise ValueError('Changed original trajectory')
    choices = complete_choices(before)
    if len(choices) != 191:
        raise ValueError('Changed frozen selection size')
    cp = learner['checkpoints'][0]
    sample = int(digest([1702, 1, f['case']])[:16], 16)
    source_manifest = json.loads((ROOT/old['trace_path']).read_text().splitlines()[0])['data']
    if source_manifest['sample_seed'] != sample:
        raise ValueError('Changed policy sampling seed')
    current, data = episode(f, {**v, 'checkpoint': cp}, 'original_sample_complete_menu',
                            model=load_model(cp, v), sample_seed=sample)
    report = dict(manifest=v, source_training=dict(path=str(source_path.relative_to(ROOT)), sha256=file_hash(source_path)),
                  source_failure=old, checkpoint=cp, primary=compact(current), legal_choices=len(choices),
                  old_transition_match=current['plan'][:18] == expected,
                  encoded_choices_at_failure=len(data[18]['encoded'][1]) if len(data)>18 else None,
                  replays=[])
    if current['status'] in ('clear', 'defeat') and report['old_transition_match']:
        for i in range(3):
            replay, _ = episode(f, v, f'independent_full_prefix:{i}', expected=current['plan'])
            replay['match'] = matched(current, replay)
            report['replays'].append(compact(replay))
    report['passed'] = (report['old_transition_match'] and report['encoded_choices_at_failure']==191
                        and len(report['replays'])==3 and all(r['match'] for r in report['replays']))
    report['audit'] = audit(report); report['passed'] &= report['audit']['pass']
    report['seconds'] = time.monotonic()-started
    write(output, report)
    print(json.dumps({k: report[k] for k in ('passed', 'legal_choices', 'old_transition_match',
                      'encoded_choices_at_failure', 'audit', 'seconds')} | {'status': current['status'], 'error': current.get('error')}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output', required=True); a=p.parse_args()
    if Path(a.output).exists(): raise ValueError('Preserve old evidence')
    main(Path(a.output))
