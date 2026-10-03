#!/usr/bin/env python3
"""Frozen, bounded uniform root teacher with held-out continuation streams."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash
from rsi.phase_rl import controller, ENCODER
from rsi.research_restore import ENGINE_KEYS
from rsi.root_teacher import candidates, rollout, select_mean, source_roots, utility
from rsi.run_env import run, replay
from scripts.evaluate_battle_search_e120 import manifest, write, audit
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.train_curriculum_e153 import full_summary


def checked(path, expected=None, tracked=False):
    path = Path(path)
    if expected is not None and file_hash(path) != expected:
        raise ValueError('Changed evidence '+str(path))
    if tracked:
        subprocess.run(['git', 'ls-files', '--error-unmatch', str(path.resolve().relative_to(ROOT))],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return json.loads(path.read_text())


def info(path):
    path = Path(path)
    return dict(path=str(path.resolve().relative_to(ROOT)), sha256=file_hash(path))


def cpu():
    return sum(x.ru_utime+x.ru_stime for x in
               (resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)))


def parallel(fn, items, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def version():
    v = {**manifest(), 'experiment': 'E149', 'encoder': ENCODER, 'torch': str(torch.__version__), 'device': 'cpu'}
    evidence = checked(ROOT/'experiments/E154/validation-v2.json')
    if not evidence['pass'] or any(v[k] != evidence['manifest'][k] for k in ENGINE_KEYS):
        raise ValueError('Runtime does not match guarded E154 compatibility evidence')
    return v


def same_runtime(plan, v):
    if any(plan['manifest'][k] != v[k] for k in ENGINE_KEYS):
        raise ValueError('Frozen runtime changed')


def plan(v, output, **_):
    cp = checked(ROOT/'experiments/E140/training-v2.json')['learners'][1]['bc']
    model = load_phase(cp)
    configs = [dict(case=f'train-A{a}-{i:03}', seed=f'e149_train_Ironclad_A{a}_{i:03}',
        character='Ironclad', ascension=a, index=i, split='train', arm='neural_all')
        for a in (0, 5, 10) for i in range(5)]
    return dict(manifest=v, checkpoint=cp, parameters=sum(p.numel() for p in model.parameters()),
        collection=configs, budgets=dict(collect=180, bank=240, evaluate=900, cpu=1800,
                                       local_seconds=30, full_seconds=90, search_p95=60),
        discovery_repeats=4, validation_repeats=6, candidates=4,
        bootstrap=dict(seed=149, repeats=10000, cluster='game_seed'),
        known_unsupported=[dict(mechanic='Crystal Sphere', issue=64), dict(mechanic='Trial', issue=294)],
        foundation=dict(e154=info(ROOT/'experiments/E154/validation-v2.json'),
            restoration='full prefix; old certificates not applied across runtime versions',
            native_equivalence_claim=False), final_acceptance_seeds_unused=True)


def collect(v, output, plan_path, **_):
    p = checked(plan_path, tracked=True)
    same_runtime(p, v)
    model = load_phase(p['checkpoint'])
    started = time.monotonic()
    deadline = started+p['budgets']['collect']
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    def one(c):
        r = run(c, v, controller=controller(model), seconds=max(.001, min(90, deadline-time.monotonic())))
        if c['index'] == 0 and r['status'] in ('victory', 'defeat'):
            r['verification'] = replay(r, v, seconds=max(.001, min(90, deadline-time.monotonic())))
        write(directory/(c['case']+'.json'), r)
        print(json.dumps(dict(case=c['case'], status=r['status'], entries=len(r['entries']))), flush=True)
        return r
    records = parallel(one, p['collection'])
    proof = audit(records)
    return dict(manifest=v, plan_sha256=file_hash(plan_path), records=records, summary=full_summary(records),
        seconds=time.monotonic()-started, audit=proof,
        execution_pass=proof['pass'] and time.monotonic()-started <= p['budgets']['collect'] and
            all(r['status'] in ('victory', 'defeat') and r.get('verification', {}).get('status', 'match') == 'match'
                for r in records))


def bank(v, output, plan_path, collection_path, **_):
    p = checked(plan_path, tracked=True)
    same_runtime(p, v)
    collection = checked(collection_path, tracked=True)
    if not collection['execution_pass'] or collection['plan_sha256'] != file_hash(plan_path):
        raise ValueError('Incomplete or mismatched source collection')
    if [r['seed'] for r in collection['records']] != [c['seed'] for c in p['collection']]:
        raise ValueError('Collection cohort changed')
    model = load_phase(p['checkpoint'])
    started = time.monotonic()
    deadline = started+p['budgets']['bank']
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    rows, preflights = [], []
    for record in collection['records']:
        for root, state in source_roots(record):
            index = len(rows)
            root['candidate_set'] = candidates(model, root, state)
            path = directory/f'root-{index:02}.json'
            write(path, root)
            rows.append({k: root[k] for k in ('case', 'seed', 'ascension', 'mode', 'reference_room_type',
                'root_phase', 'root_context', 'root_hash', 'prefix_hash')} |
                dict(index=index, raw=info(path), candidates=root['candidate_set']))
            if record['index'] == 0:
                r = rollout(root, v, model, 'preflight:greedy',
                    first_action=root['candidate_set']['actions'][0],
                    seconds=max(.001, min(30, deadline-time.monotonic())))
                check = rollout(root, v, model, 'preflight:independent-replay', expected=r['plan'],
                    seconds=max(.001, min(30, deadline-time.monotonic())))
                preflights.append(dict(case=root['case'], reference=compact(r), replay=compact(check),
                    passed=r['status'] in ('clear', 'defeat') and r['status'] == check['status'] and
                        r['plan'] == check['plan'] and r['final_hash'] == check['final_hash']))
    proof = audit(preflights)
    return dict(manifest=v, plan_sha256=file_hash(plan_path), collection=info(collection_path),
        roots=rows, preflights=preflights, seconds=time.monotonic()-started, audit=proof,
        passed=len(rows) == 30 and len(preflights) == 6 and all(x['passed'] for x in preflights) and
            proof['pass'] and time.monotonic()-started <= p['budgets']['bank'])


def stats(rs):
    values = [utility(r) for r in rs]
    return dict(n=len(values), mean=float(np.mean(values)), variance=float(np.var(values, ddof=1)) if len(values)>1 else 0.,
        clears=sum(r['status'] == 'clear' for r in rs), hp_mean=float(np.mean([r['hp'] for r in rs])),
        potions_mean=float(np.mean([len(r['potions']) for r in rs])))


def summarize(records, p, seconds, cpu_seconds, proof):
    complete = len(records) == 30 and all(r['status'] == 'complete' for r in records)
    result = dict(roots=len(records), complete=complete, statuses=dict(Counter(r['status'] for r in records)),
        teacher_gate=False, final_acceptance_seeds_unused=True)
    if not complete:
        return result
    cluster = defaultdict(list)
    for r in records:
        cluster[r['seed']].append(r['validation_delta'])
    seed_delta = np.asarray([np.mean(xs) for xs in cluster.values()])
    rng = np.random.default_rng(p['bootstrap']['seed'])
    means = seed_delta[rng.integers(len(seed_delta), size=(p['bootstrap']['repeats'], len(seed_delta)))].mean(axis=1)
    by_mode = {m: float(np.mean([r['validation_delta'] for r in records if r['mode'] == m])) for m in ('combat', 'prepare')}
    by_asc = {str(a): float(np.mean([r['validation_delta'] for r in records if r['ascension'] == a])) for a in (0, 5, 10)}
    greedy_delta = float(np.mean([utility(r['greedy']['selected'])-utility(r['greedy']['actor']) for r in records]))
    counts = {arm: dict(local_clears=sum(r['greedy'][arm]['status'] == 'clear' for r in records),
        suffix_act2=sum(2 in r['full'][arm]['acts_seen'] for r in records),
        suffix_act3=sum(3 in r['full'][arm]['acts_seen'] for r in records),
        suffix_victories=sum(r['full'][arm]['status'] == 'victory' for r in records)) for arm in ('actor', 'selected')}
    p95 = float(np.quantile([r['search_seconds'] for r in records], .95))
    values = [x for r in records for xs in r['discovery'] for x in xs]
    values += [x for r in records for arm in ('actor', 'selected') for x in r['validation'][arm]]
    values += [r[name][arm] for r in records for name in ('greedy', 'full') for arm in ('actor', 'selected')]
    no_lost_victory = all(r['full']['actor']['status'] != 'victory' or r['full']['selected']['status'] == 'victory' for r in records)
    gates = dict(execution=complete and proof['pass'], effect=float(seed_delta.mean()) >= .05,
        lower_bound=float(np.quantile(means, .025)) > 0, positive_seeds=int(sum(seed_delta > 0)) >= 5,
        no_stratum_regression=all(x >= 0 for x in [*by_mode.values(), *by_asc.values()]),
        greedy_no_regression=greedy_delta >= 0 and counts['selected']['local_clears'] >= counts['actor']['local_clears'],
        full_transfer_no_regression=counts['selected']['suffix_act2'] >= counts['actor']['suffix_act2'] and no_lost_victory,
        latency=p95 <= p['budgets']['search_p95'], budget=seconds <= p['budgets']['evaluate'] and cpu_seconds <= p['budgets']['cpu'])
    result.update(validation_delta=float(seed_delta.mean()), cluster95=np.quantile(means, [.025, .975]).tolist(),
        independent_game_seeds=len(cluster), positive_seeds=int(sum(seed_delta > 0)),
        by_mode=by_mode, by_ascension=by_asc, changed_actions=sum(r['selected_index'] != 0 for r in records),
        greedy_utility_delta=greedy_delta, counts=counts, search_p95_seconds=p95,
        paths=len(values), path_statuses=dict(Counter(x['status'] for x in values)),
        restore_seconds=sum(x.get('restore_seconds', 0) for x in values),
        summed_path_seconds=sum(x['seconds'] for x in values),
        engine_commands=sum(x.get('restore_commands', 0)+x['steps'] for x in values),
        continuation_actions=sum(x['steps'] for x in values), gates=gates, teacher_gate=all(gates.values()))
    return result


def evaluate(v, output, plan_path, bank_path, **_):
    p = checked(plan_path, tracked=True)
    same_runtime(p, v)
    b = checked(bank_path, tracked=True)
    same_runtime(b, v)
    source_hash = file_hash(plan_path)
    if 'source_plan' in p:
        source = checked(ROOT/p['source_plan']['path'], p['source_plan']['sha256'], tracked=True)
        proof = checked(ROOT/p['scheduling_proof']['path'], p['scheduling_proof']['sha256'], tracked=True)
        if {k:val for k,val in p.items() if k not in ('source_plan','scheduling_proof','workers')} != source:
            raise ValueError('Scheduling revision changed the learning protocol')
        if not proof['passed'] or not any(r['workers']==p['workers'] for r in proof['rounds']):
            raise ValueError('Scheduling revision lacks matching replay diagnostic')
        source_hash = p['source_plan']['sha256']
    if not b['passed'] or b['plan_sha256'] != source_hash:
        raise ValueError('Unverified teacher roots')
    model = load_phase(p['checkpoint'])
    started, cpu_start = time.monotonic(), cpu()
    deadline = started+p['budgets']['evaluate']
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)

    def one(meta):
        index = meta['index']
        root = checked(ROOT/meta['raw']['path'], meta['raw']['sha256'])
        actions = root['candidate_set']['actions']
        row = {k: meta[k] for k in ('case', 'seed', 'mode', 'ascension')} | dict(status='unstarted', discovery=[])
        def episode(label, action, seed=None, full=False):
            if time.monotonic() >= deadline or cpu()-cpu_start >= p['budgets']['cpu']:
                raise TimeoutError('Global teacher budget; remaining paths unstarted')
            budget = p['budgets']['full_seconds' if full else 'local_seconds']
            r = rollout(root, v, model, label, first_action=action, sample_seed=seed,
                full=full, seconds=min(budget, deadline-time.monotonic()))
            if r['status'] not in (('victory', 'defeat') if full else ('clear', 'defeat')):
                row['failed_probe'] = compact(r)
                raise ValueError('Incomplete continuation: '+r['status'])
            return compact(r)
        try:
            clock = time.monotonic()
            for j, action in enumerate(actions):
                group = []
                row['discovery'].append(group)
                for k in range(p['discovery_repeats']):
                    group.append(episode(f'discovery:{j}:{k}', action, 14900000+index*100+k))
            row['search_seconds'] = time.monotonic()-clock
            row['selected_index'] = select_mean(row['discovery'])
            row['discovery_stats'] = [stats(rs) for rs in row['discovery']]
            row['selected_action'] = actions[row['selected_index']]
            row['actor_action'] = actions[0]
            # Persist selection BEFORE any independent validation can be observed.
            write(directory/f'root-{index:02}-selection.json', row)
            row.update(validation={}, greedy={}, full={})
            for arm, action in [('actor', actions[0]), ('selected', row['selected_action'])]:
                row['validation'][arm] = []
                for k in range(p['validation_repeats']):
                    row['validation'][arm].append(episode(f'validation:{arm}:{k}', action, 14910000+index*100+k))
                row['greedy'][arm] = episode('greedy:'+arm, action)
                row['full'][arm] = episode('full:'+arm, action, full=True)
            row['validation_stats'] = {arm: stats(rs) for arm, rs in row['validation'].items()}
            row['validation_delta'] = row['validation_stats']['selected']['mean']-row['validation_stats']['actor']['mean']
            row['selection_optimism'] = row['discovery_stats'][row['selected_index']]['mean']-row['validation_stats']['selected']['mean']
            row['status'] = 'complete'
        except Exception as exc:
            row.update(status='incomplete', error=f'{type(exc).__name__}: {exc}')
        write(directory/f'root-{index:02}.json', row)
        print(json.dumps({k: row.get(k) for k in ('case', 'status', 'selected_index', 'validation_delta', 'error')}), flush=True)
        return row
    records = parallel(one, b['roots'], workers=p.get('workers',8))
    seconds, used = time.monotonic()-started, cpu()-cpu_start
    proof = audit(records)
    return dict(manifest=v, plan_sha256=file_hash(plan_path), bank_sha256=file_hash(bank_path),
        records=records, seconds=seconds, cpu_seconds=used, audit=proof,
        summary=summarize(records, p, seconds, used, proof))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('plan', 'collect', 'bank', 'evaluate'))
    for name in ('plan', 'collection', 'bank'):
        parser.add_argument('--'+name, dest=name+'_path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = vars(parser.parse_args())
    if args['output'].exists():
        raise ValueError('Never overwrite an experiment attempt')
    torch.set_num_threads(1)
    mode = args.pop('mode')
    result = globals()[mode](v=version(), **args)
    write(args['output'], result)
    print(json.dumps({k: result[k] for k in ('summary', 'passed', 'execution_pass', 'seconds', 'cpu_seconds', 'audit') if k in result}), flush=True)
