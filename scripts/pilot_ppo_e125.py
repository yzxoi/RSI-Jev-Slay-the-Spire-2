#!/usr/bin/env python3
"""Fixed E125 phases; no automatic sweeps, test selection or game modification."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact, fixture
from rsi.checkpoints import file_hash
from rsi.ppo import ActorCritic, ENCODER_VERSION, HP, update
from rsi.ppo_env import episode
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, manifest, write

SPLITS = {name: [f'e125_20261002_{name}_{i:02}' for i in range(n)]
          for name, n in [('train', 16), ('val', 8), ('test', 16)]}
LEARNERS = (1701, 1702)
BANK = ROOT / 'experiments/E125/fixtures.json'


def version():
    return {**manifest(), 'experiment': 'E125', 'encoder': ENCODER_VERSION,
            'torch': str(torch.__version__), 'numpy': str(np.__version__), 'device': 'cpu',
            'torch_threads': torch.get_num_threads(), 'hyperparameters': HP, 'splits': SPLITS,
            'learner_seeds': LEARNERS, 'scope': 'Ironclad A0 first Elite; no full runs'}


def pool_map(function, items):
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(function, items))


def bank(version):
    b = json.loads(BANK.read_text())
    expected = [s for seeds in SPLITS.values() for s in seeds]
    if [f['seed'] for f in b['fixtures']] != expected or any(f['status'] != 'ready' for f in b['fixtures']):
        raise ValueError('Incomplete/replaced/reordered frozen seed bank')
    for k in ('headless_game_sha256', 'headless_assembly_sha256', 'game_dll_sha256'):
        if b['manifest'][k] != version[k]:
            raise ValueError('Engine changed after freeze')
    return b


def entries(b, split):
    return [f for f in b['fixtures'] if f['seed'] in SPLITS[split]]


def summarize(records):
    terminal = [r for r in records if r['status'] in ('clear', 'defeat')]
    return {'n': len(records), 'statuses': dict(Counter(r['status'] for r in records)),
            'clears': sum(r['status'] == 'clear' for r in records),
            'mean_reward': statistics.mean(r['reward'] for r in terminal) if terminal else None,
            'mean_clear_hp': statistics.mean(r['hp'] for r in terminal if r['status'] == 'clear')
                             if any(r['status'] == 'clear' for r in terminal) else None,
            'steps': sum(r['steps'] for r in records),
            'engine_seconds': sum(r['seconds'] for r in records),
            'inference_seconds': sum(r.get('inference_seconds', 0) for r in records),
            'illegal_actions': sum(r.get('illegal_actions', 0) for r in records)}


def valid(records):
    return all(r['status'] in ('clear', 'defeat') and r['entry_verified']
               and not r['illegal_actions'] for r in records)


def evaluate(fixtures, v, label, model=None, verify=False):
    def run(f):
        r, _ = episode(f, v, label, model=model)
        if verify and r['status'] in ('clear', 'defeat'):
            check, _ = episode(f, v, label + ':verification', expected=r['plan'])
            match = all(check.get(k) == r.get(k) for k in ('status', 'final_hash', 'transition_hash', 'steps'))
            r['verification'] = compact(check); r['verification_match'] = match
        return compact(r)
    records = pool_map(run, fixtures)
    return {'label': label, 'records': records, 'summary': summarize(records),
            'pass': valid(records) and (not verify or all(r.get('verification_match') for r in records))}


def freeze(v, output):
    configs = [dict(case=f'{split}-{i:02}', seed=seed, character='Ironclad', ascension=0,
                    index=j) for j, (split, i, seed) in enumerate(
                        (split, i, seed) for split, seeds in SPLITS.items() for i, seed in enumerate(seeds))]
    start = time.monotonic()
    records = pool_map(lambda c: fixture(c, v), configs)
    r = {'manifest': v, 'configs': configs, 'fixtures': records,
         'seconds': time.monotonic() - start, 'pass': all(f['status'] == 'ready' for f in records)}
    r['audit'] = audit(r); write(output, r)
    print(json.dumps({'pass': r['pass'], 'audit': r['audit'],
                      'statuses': dict(Counter(f['status'] for f in records)), 'seconds': r['seconds']}), flush=True)


def save_checkpoint(path, model, optimizer, learner, index, v):
    torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                'learner': learner, 'update': index, 'manifest': v,
                'bank_sha256': file_hash(BANK)}, path)
    return {'path': str(path.relative_to(ROOT)), 'sha256': file_hash(path), 'update': index}


def load_checkpoint(record, v):
    path = ROOT / record['path']
    if file_hash(path) != record['sha256']:
        raise ValueError('Model checkpoint hash mismatch')
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if saved['bank_sha256'] != file_hash(BANK) or saved['manifest']['encoder'] != ENCODER_VERSION:
        raise ValueError('Checkpoint data/encoder mismatch')
    for k in ('headless_game_sha256', 'headless_assembly_sha256', 'game_dll_sha256'):
        if saved['manifest'][k] != v[k]:
            raise ValueError('Checkpoint engine mismatch')
    model = ActorCritic(); model.load_state_dict(saved['model']); model.eval()
    return model


def train(v, b, output, preflight):
    p = json.loads(Path(preflight).read_text())
    if not p['evaluation']['pass'] or p['bank_sha256'] != file_hash(BANK):
        raise ValueError('Complete preflight required before training')
    directory = output.with_suffix('')
    if directory.exists():
        raise ValueError('Preserve previous/partial training directory')
    directory.mkdir(parents=True)
    report = {'manifest': v, 'bank_sha256': file_hash(BANK),
              'preflight': {'path': preflight, 'sha256': file_hash(preflight)}, 'learners': [], 'pass': True}
    for learner in LEARNERS:
        started = time.monotonic(); work_seconds = 0.
        torch.manual_seed(learner); rng = np.random.default_rng(learner)
        model = ActorCritic(); optimizer = torch.optim.Adam(model.parameters(), lr=HP['lr'], eps=1e-5)
        row = {'learner': learner, 'parameters': sum(p.numel() for p in model.parameters()),
               'updates': [], 'checkpoints': [], 'validations': [], 'status': 'running'}
        report['learners'].append(row)
        initial = save_checkpoint(directory / f'{learner}-00.pt', model, optimizer, learner, 0, v)
        row['checkpoints'].append(initial)
        first = evaluate(entries(b, 'val'), {**v, 'checkpoint': initial}, f'{learner}:val:0', model)
        first['update'] = 0; row['validations'].append(first)
        if not first['pass']:
            row['status'] = 'invalid'; report['pass'] = False
            write(directory / f'{learner}.json', row)
            break
        for index in range(1, 13):
            if work_seconds >= 1200:
                row['status'] = 'training_time_cap'; break
            start = time.monotonic()
            configs = [(f, k) for k in range(2) for f in entries(b, 'train')]
            def collect(item):
                f, k = item
                seed = int(digest([learner, index, f['case'], k])[:16], 16)
                return episode(f, {**v, 'checkpoint': row['checkpoints'][-1]},
                               f'{learner}:train:{index}:{k}', model=model, sample_seed=seed)
            collected = pool_map(collect, configs)
            records = [compact(r) for r, _ in collected]
            step = {'update': index, 'episodes': records, 'summary': summarize(records)}
            if not valid(records):
                step['optimizer_skipped'] = True; row['status'] = 'invalid'; report['pass'] = False
                row['updates'].append(step); break
            opt_start = time.monotonic()
            step['optimization'] = update(model, optimizer, [(data, r['reward']) for r, data in collected], rng)
            step['optimization_seconds'] = time.monotonic() - opt_start
            step['collection_and_optimization_seconds'] = time.monotonic() - start
            work_seconds += step['collection_and_optimization_seconds']
            row['updates'].append(step)
            cp = save_checkpoint(directory / f'{learner}-{index:02}.pt', model, optimizer, learner, index, v)
            row['checkpoints'].append(cp)
            print(json.dumps({'learner': learner, 'update': index, 'summary': step['summary'],
                              'optimization': step['optimization'], 'work_seconds': work_seconds}), flush=True)
            if index in (4, 8, 12):
                val = evaluate(entries(b, 'val'), {**v, 'checkpoint': cp}, f'{learner}:val:{index}', model)
                val['update'] = index; row['validations'].append(val)
                print(json.dumps({'learner': learner, 'validation': index, **val['summary']}), flush=True)
                if not val['pass']:
                    row['status'] = 'invalid'; report['pass'] = False; break
            write(directory / f'{learner}.json', row)
        else:
            row['status'] = 'complete'
        if row['status'] != 'invalid':
            best = max(row['validations'], key=lambda x: (x['summary']['clears'], x['summary']['mean_reward'], -x['update']))
            row['selected'] = next(cp for cp in row['checkpoints'] if cp['update'] == best['update'])
        row['work_seconds'] = work_seconds; row['seconds'] = time.monotonic() - started
        write(directory / f'{learner}.json', row)
        if not report['pass']:
            break
    report['audit'] = audit(report); write(output, report)
    print(json.dumps({'pass': report['pass'], 'audit': report['audit'],
                      'selected': [r.get('selected') for r in report['learners']]}), flush=True)


def paired_delta(a, b):
    def score(r):
        return r['hp'] if r['status'] == 'clear' else 0
    if [r['case'] for r in a['records']] != [r['case'] for r in b['records']]:
        raise ValueError('Unpaired test seeds')
    diffs = [score(x) - score(y) for x, y in zip(a['records'], b['records'])]
    return {'clear_delta': a['summary']['clears'] - b['summary']['clears'],
            'hp_equivalent_deltas': diffs, 'median_hp_delta': statistics.median(diffs),
            'mean_hp_delta': statistics.mean(diffs)}


def test(v, b, output, training):
    t = json.loads(Path(training).read_text())
    if not t['pass'] or len(t['learners']) != 2 or t['bank_sha256'] != file_hash(BANK):
        raise ValueError('Both valid training replicates required before test')
    # Output commitment exists before any test outcome is generated.
    directory = output.with_suffix('')
    if directory.exists():
        raise ValueError('Preserve previous/partial test directory')
    directory.mkdir(parents=True)
    selected = {str(r['learner']): r['selected'] for r in t['learners']}
    write(directory / 'selection-before-test.json', {'training_sha256': file_hash(training), 'selected': selected})
    start = time.monotonic()
    planner = evaluate(entries(b, 'test'), v, 'test:planner')
    report = {'manifest': v, 'bank_sha256': file_hash(BANK), 'training_sha256': file_hash(training),
              'selection_before_test_sha256': file_hash(directory / 'selection-before-test.json'),
              'planner': planner, 'learners': [], 'pass': planner['pass']}
    write(directory / 'planner.json', planner)
    for row in t['learners']:
        initial_cp, selected_cp = row['checkpoints'][0], row['selected']
        initial = evaluate(entries(b, 'test'), {**v, 'checkpoint': initial_cp}, f"test:{row['learner']}:initial", load_checkpoint(initial_cp, v))
        chosen = evaluate(entries(b, 'test'), {**v, 'checkpoint': selected_cp}, f"test:{row['learner']}:selected", load_checkpoint(selected_cp, v), verify=True)
        result = {'learner': row['learner'], 'selected': selected_cp, 'initial': initial, 'trained': chosen}
        passed = initial['pass'] and chosen['pass'] and planner['pass']
        result['infrastructure_pass'] = passed
        if passed:
            d, p = paired_delta(chosen, initial), paired_delta(chosen, planner)
            result.update(versus_initial=d, versus_planner=p,
                          strength_pass=bool((d['clear_delta'] >= 2 or
                              (d['clear_delta'] == 0 and d['median_hp_delta'] >= 3)) and
                              p['clear_delta'] >= 0 and p['median_hp_delta'] >= -5))
        else:
            result['strength_pass'] = False
        report['pass'] &= passed; report['learners'].append(result)
        write(directory / f"{row['learner']}.json", result)
        print(json.dumps({'learner': row['learner'], 'initial': initial['summary'], 'selected': chosen['summary'],
                          'strength_pass': result['strength_pass']}), flush=True)
    report['continue_training_gate'] = report['pass'] and all(r['strength_pass'] for r in report['learners'])
    report['seconds'] = time.monotonic() - start
    report['audit'] = audit(report); write(output, report)
    print(json.dumps({'pass': report['pass'], 'continue_training_gate': report['continue_training_gate'], 'audit': report['audit']}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('freeze', 'preflight', 'train', 'test'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--training')
    args = parser.parse_args()
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError('Do not overwrite evidence')
    output.parent.mkdir(parents=True, exist_ok=True)
    v = version()
    if args.phase == 'freeze':
        freeze(v, output)
    else:
        b = bank(v)
        if args.phase == 'preflight':
            result = {'manifest': v, 'bank_sha256': file_hash(BANK),
                      'evaluation': evaluate(entries(b, 'val'), v, 'preflight:planner', verify=True)}
            result['audit'] = audit(result); write(output, result)
            print(json.dumps({'pass': result['evaluation']['pass'], 'audit': result['audit'],
                              'summary': result['evaluation']['summary']}), flush=True)
        elif args.phase == 'train':
            train(v, b, output, args.preflight)
        else:
            test(v, b, output, args.training)


if __name__ == '__main__':
    main()
