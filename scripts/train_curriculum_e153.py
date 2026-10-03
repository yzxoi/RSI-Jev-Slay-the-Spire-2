#!/usr/bin/env python3
"""Real-fight curriculum with preparation credit and whole-run monitoring."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.curriculum import ROOMS, roots, episode, cautious_macro
from rsi.checkpoints import file_hash
from rsi.phase_rl import controller, ENCODER
from rsi.ppo import update
from rsi.run_env import run, replay
from scripts.evaluate_battle_search_e120 import manifest, write, audit
from scripts.pilot_fullpolicy_e140 import load_phase, save
from scripts.pilot_onpolicy_e146 import CONFIG, behavior_parity
from scripts.probe_task_value_e148 import checked

LEARNERS = (2301, 2302)
STAGES = (
    ('Monster', [('combat', 'Monster', 12), ('prepare', 'Monster', 12)]),
    ('Elite', [('combat', 'Monster', 6), ('combat', 'Elite', 12), ('prepare', 'Elite', 6)]),
    ('Boss', [('combat', 'Monster', 6), ('combat', 'Elite', 6), ('combat', 'Boss', 6), ('prepare', 'Boss', 6)]))


def info(path):
    return dict(path=str(path.resolve().relative_to(ROOT)), sha256=file_hash(path))


def pool(fn, values):
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(fn, values))


def natural_configs(split, n, ascensions=(0, 5, 10)):
    return [dict(case=f'{split}-A{a}-{i:03}', seed=f'e153_{split}_Ironclad_A{a}_{i:03}',
        character='Ironclad', ascension=a, index=i, split=split, arm='planner')
        for a in ascensions for i in range(n)]


def plan(v, output):
    sources = {e: info(ROOT/f'experiments/{e}/{filename}.json') for e, filename in
        (('E133', 'fixtures-v2'), ('E139', 'bank-v1'), ('E140', 'training-v2'))}
    cp = checked(ROOT/sources['E140']['path'])['learners'][1]['bc']
    load_phase(cp)
    result = dict(manifest=v, sources=sources, behavior=cp, learners=LEARNERS, ppo=CONFIG,
        stages=STAGES, updates_per_stage=2, collection=natural_configs('train', 18)+natural_configs('dev', 12),
        monitors=natural_configs('monitor', 3), tests=natural_configs('test', 3, range(11)),
        budgets=dict(collect=900, bank=180, train_per_learner=900, evaluate=900),
        final_acceptance_seeds_unused=True)
    write(output, result)
    return result


def full_summary(records):
    if not records:
        return {}
    return dict(attempts=len(records), seeds=len({r['seed'] for r in records}),
        statuses=dict(Counter(r['status'] for r in records)),
        act2=sum(2 in r['acts_seen'] for r in records), act3=sum(3 in r['acts_seen'] for r in records),
        boss_entries=sum(e['room_type'] == 'Boss' for r in records for e in r['entries']),
        median_floor=float(np.median([r['max_floor'] for r in records])),
        maximum_floor=max(r['max_floor'] for r in records),
        phases=dict(sum((Counter(r['scenes']) for r in records), Counter())))


def collect(v, plan_path, output):
    p = checked(plan_path)
    t = time.monotonic()
    deadline = t+p['budgets']['collect']
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)

    def one(c):
        r = run(c, v, macro_controller=cautious_macro, seconds=min(180, max(.001, deadline-time.monotonic())))
        if c['index'] == 0 and r['status'] in ('victory', 'defeat'):
            r['verification'] = replay(r, v, seconds=min(180, max(.001, deadline-time.monotonic())))
        write(directory/(c['case']+'.json'), r)
        print(json.dumps({k: r[k] for k in ('case', 'status', 'max_floor')} |
                         {'rooms': dict(Counter(e['room_type'] for e in r['entries']))}), flush=True)
        return r

    records = pool(one, p['collection'])
    result = dict(manifest=v, plan_sha256=file_hash(plan_path), records=records, summary=full_summary(records),
        audit=audit(records), seconds=time.monotonic()-t)
    result['execution_pass'] = result['audit']['pass'] and all(r['status'] in ('victory', 'defeat') and
        r.get('verification', {}).get('status', 'match') == 'match' for r in records) and result['seconds'] <= p['budgets']['collect']
    write(output, result)
    return result


def interleave(fs):
    by = defaultdict(list)
    for f in sorted(fs, key=lambda f: (f['seed'], f['case'])):
        by[f['ascension']].append(f)
    return [by[a][i] for i in range(max(map(len, by.values()), default=0))
            for a in sorted(by) if i < len(by[a])]


def build_bank(v, plan_path, collection_path, output):
    t = time.monotonic()
    p, collection = checked(plan_path), checked(collection_path)
    if not collection['execution_pass'] or collection['plan_sha256'] != file_hash(plan_path):
        raise ValueError('Incomplete natural cohort')
    for source in p['sources'].values():
        if file_hash(ROOT/source['path']) != source['sha256']:
            raise ValueError('Changed original source')
    old = checked(ROOT/p['sources']['E133']['path'])
    full = checked(ROOT/p['sources']['E139']['path'])
    fs = []
    for r in old['seeds']:
        if r['split'] == 'train':
            fs.extend(roots(r))
    for r in full['records']:
        if r['split'] == 'train' and r['character'] == 'Ironclad':
            fs.extend(roots(r, wanted=('Boss',)))
    for r in collection['records']:
        fs.extend(roots(r))
    if len({(f['seed'], f['mode'], f['root_hash']) for f in fs}) != len(fs):
        raise ValueError('Duplicate natural curriculum root')
    counts = {split: {room: dict(
        combat_roots=len([f for f in fs if f['split'] == split and f['mode'] == 'combat' and f['reference_room_type'] == room]),
        game_seeds=len({f['seed'] for f in fs if f['split'] == split and f['reference_room_type'] == room}),
        by_difficulty=dict(Counter(str(f['ascension']) for f in fs if f['split'] == split and f['mode'] == 'combat' and f['reference_room_type'] == room)),
        by_act=dict(Counter(str(f['reference_act']) for f in fs if f['split'] == split and f['mode'] == 'combat' and f['reference_room_type'] == room)))
        for room in ROOMS} for split in ('train', 'dev')}
    coverage = all(counts['train'][room]['game_seeds'] >= 3 for room in ROOMS)
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    fixture_path = directory/'roots.json'
    write(fixture_path, fs)
    checks = []
    if coverage:
        model = load_phase(p['behavior'])
        selected = [next(f for f in fs if f['split'] == 'train' and f['mode'] == mode and f['reference_room_type'] == room)
                    for room in ROOMS for mode in ('combat', 'prepare')]

        def verify(f):
            r, _ = episode(f, v, 'boundary-preflight', model=model,
                           seconds=min(60, max(.001, t+p['budgets']['bank']-time.monotonic())))
            if r['status'] in ('clear', 'defeat'):
                rr, _ = episode(f, v, 'boundary-replay', expected=r['plan'],
                                seconds=min(60, max(.001, t+p['budgets']['bank']-time.monotonic())))
                r['verification'] = rr
                r['verified'] = all(r[k] == rr[k] for k in ('status', 'steps', 'final_hash', 'transition_hash'))
            return r
        checks = pool(verify, selected)
    out = dict(manifest=v, plan_sha256=file_hash(plan_path), collection_sha256=file_hash(collection_path),
        fixtures=info(fixture_path), coverage=counts, train_coverage_pass=coverage,
        root_index=[{k: value for k, value in f.items() if k not in ('prefix', 'previous')} for f in fs],
        preflight=checks, audit=audit(checks), seconds=time.monotonic()-t)
    out['execution_pass'] = coverage and all(r.get('verified') for r in checks) and out['audit']['pass'] and out['seconds'] <= p['budgets']['bank']
    write(output, out)
    return out


def load_roots(bank):
    if not bank['execution_pass'] or file_hash(ROOT/bank['fixtures']['path']) != bank['fixtures']['sha256']:
        raise ValueError('Unfrozen/unverified curriculum bank')
    return json.loads((ROOT/bank['fixtures']['path']).read_text())


def full_panel(configs, v, cp, label, deadline, verify=False, planner=False):
    model = None if planner else load_phase(cp)

    def one(base):
        c = {**base, 'case': label+':'+base['case'], 'actor': label,
             'arm': 'planner' if planner else 'neural_all'}
        r = run(c, {**v, 'behavior_checkpoint': cp},
            controller=None if planner else controller(model), macro_controller=cautious_macro,
            seconds=min(180, max(.001, deadline-time.monotonic())))
        if verify and base['index'] == 0 and r['status'] in ('victory', 'defeat'):
            r['verification'] = replay(r, v, seconds=min(180, max(.001, deadline-time.monotonic())))
        print(json.dumps(dict(phase='full_run', actor=label, case=r['case'], status=r['status'], floor=r['max_floor'])), flush=True)
        return r
    return pool(one, configs)


def full_valid(rows):
    return all(r['status'] in ('victory', 'defeat') and r.get('verification', {}).get('status', 'match') == 'match'
               and (r['arm'] != 'neural_all' or r['network_calls'] == r['steps'] and r['planner_calls'] == 0) for r in rows)


def train(v, plan_path, bank_path, output):
    p, bank = checked(plan_path), checked(bank_path)
    fs = load_roots(bank)
    pools = {(mode, room): interleave([f for f in fs if f['split'] == 'train' and f['mode'] == mode and f['reference_room_type'] == room])
             for mode in ('combat', 'prepare') for room in ROOMS}
    if any(not x for x in pools.values()):
        raise ValueError('Missing registered curriculum stratum')
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    overall_deadline = start+1800
    out = dict(manifest=v, plan_sha256=file_hash(plan_path), bank_sha256=file_hash(bank_path), source=p['behavior'],
        settings=p, learners=[], final_acceptance_seeds_unused=True)
    out['baseline_monitor'] = full_panel(p['monitors'], v, p['behavior'], 'initial', start+180)
    if not full_valid(out['baseline_monitor']):
        out.update(execution_pass=False, stopped='incomplete baseline monitor')
        write(output, out)
        return out
    for learner in LEARNERS:
        t = time.monotonic()
        deadline = min(overall_deadline, t+p['budgets']['train_per_learner'])
        torch.manual_seed(learner)
        rng = np.random.default_rng(learner)
        model = load_phase(p['behavior'])
        with torch.no_grad():
            model.value.weight.zero_()
            model.value.bias.zero_()
        optimizer = torch.optim.Adam(model.parameters(), lr=CONFIG['lr'])
        row = dict(learner=learner, status='running', updates=[], monitors=[], parameters=sum(z.numel() for z in model.parameters()))
        row['selected'] = save(directory/f'{learner}-initial.pt', model, v, 'initial-zero-value')
        out['learners'].append(row)
        offset, stopped = defaultdict(int), False
        for stage_index, (stage, mix) in enumerate(STAGES):
            for iteration in range(2):
                fixtures = []
                for mode, room, count in mix:
                    key = (mode, room)
                    fixtures += [pools[key][(offset[key]+j) % len(pools[key])] for j in range(count)]
                    offset[key] += count
                u = stage_index*2+iteration
                before = row['selected']
                batch_start = time.monotonic()

                def one(item):
                    j, f = item
                    r, trajectory = episode(f, {**v, 'behavior_checkpoint': before}, f'{learner}:{stage}:u{u+1}',
                        model=model, sample_seed=learner*100000+u*24+j,
                        seconds=min(60, max(.001, deadline-time.monotonic())))
                    if u == 0 and j == 0 and r['status'] in ('clear', 'defeat'):
                        rr, _ = episode(f, v, 'training-independent-replay', expected=r['plan'],
                                        seconds=min(60, max(.001, deadline-time.monotonic())))
                        r['verification'] = rr
                        r['verified'] = all(r[k] == rr[k] for k in ('status', 'steps', 'final_hash', 'transition_hash'))
                    return r, trajectory

                model.eval()
                outputs = pool(one, enumerate(fixtures))
                records = [r for r, _ in outputs]
                item = dict(stage=stage, update=u+1, episodes=records, fixture_cases=[f['case'] for f in fixtures],
                            behavior_checkpoint=before, collection_seconds=time.monotonic()-batch_start)
                row['updates'].append(item)
                if any(r['status'] not in ('clear', 'defeat') or r['steps'] != len(d) or r['network_calls'] != r['steps'] or
                       not r.get('verified', True) for r, d in outputs) or time.monotonic() >= deadline:
                    row.update(status='stopped_incomplete_batch', stopped_update=u+1)
                    stopped = True
                    write(output, out)
                    break
                trajectories = [d for _, d in outputs]
                item['parity'] = behavior_parity(model, trajectories)
                item['reward_mean'] = float(np.mean([r['reward'] for r in records]))
                clock = time.monotonic()
                model.train()
                item['optimization'] = update(model, optimizer, [(d, r['reward']) for r, d in outputs], rng, hp=CONFIG)
                model.eval()
                item['optimization_seconds'] = time.monotonic()-clock
                row['selected'] = save(directory/f'{learner}-u{u+1}.pt', model, v, f'real-{stage}-u{u+1}')
                load_phase(row['selected'])  # Verify serialization before starting another game.
                item['checkpoint'] = row['selected']
                resume = directory/f'{learner}-u{u+1}-optimizer.pt'
                torch.save(dict(optimizer=optimizer.state_dict(), numpy_rng=rng.bit_generator.state,
                    torch_rng=torch.get_rng_state(), checkpoint=row['selected'], update=u+1), resume)
                item['resume_state'] = info(resume)
                print(json.dumps(dict(learner=learner, stage=stage, update=u+1,
                    outcomes=dict(Counter(r['status'] for r in records)), reward=item['reward_mean'],
                    phases=dict(sum((Counter(r['scenes']) for r in records), Counter())))), flush=True)
                write(output, out)
            if stopped:
                break
            monitored = full_panel(p['monitors'], v, row['selected'], f'{learner}-{stage}', deadline)
            row['monitors'].append(dict(stage=stage, checkpoint=row['selected'], records=monitored, summary=full_summary(monitored)))
            write(output, out)
            if not full_valid(monitored) or time.monotonic() >= deadline:
                row.update(status='stopped_incomplete_monitor')
                stopped = True
                break
        if not stopped:
            row['status'] = 'complete'
        row['seconds'] = time.monotonic()-t
        write(output, out)
    out['seconds'] = time.monotonic()-start
    out['audit'] = audit(out)
    out['execution_pass'] = out['audit']['pass'] and all(r['status'] == 'complete' for r in out['learners'])
    write(output, out)
    return out


def evaluate(v, plan_path, bank_path, training_path, output):
    p, bank, training = checked(plan_path), checked(bank_path), checked(training_path)
    if not training['execution_pass'] or training['bank_sha256'] != file_hash(bank_path):
        raise ValueError('Incomplete training')
    fs = load_roots(bank)
    panel = [f for room in ROOMS for mode in ('combat', 'prepare')
             for f in interleave([f for f in fs if f['split'] == 'dev' and f['mode'] == mode and f['reference_room_type'] == room])[:12]]
    actors = {'initial': training['source'], **{str(r['learner']): r['selected'] for r in training['learners']}}
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    t = time.monotonic()
    deadline = t+p['budgets']['evaluate']
    out = dict(manifest=v, training_sha256=file_hash(training_path), bank_sha256=file_hash(bank_path),
        actors=actors, local={}, full={}, local_panel=[f['case'] for f in panel], final_acceptance_seeds_unused=True)
    for name, cp in actors.items():
        model = load_phase(cp)
        first = {}
        for f in panel:
            first.setdefault((f['ascension'], f['reference_room_type'], f['mode']), f['case'])

        def one(f):
            r, _ = episode(f, {**v, 'behavior_checkpoint': cp}, name+':local', model=model,
                           seconds=min(60, max(.001, deadline-time.monotonic())))
            if f['mode'] == 'combat' and first[f['ascension'], f['reference_room_type'], f['mode']] == f['case'] and r['status'] in ('clear', 'defeat'):
                rr, _ = episode(f, v, name+':local-replay', expected=r['plan'],
                                seconds=min(60, max(.001, deadline-time.monotonic())))
                r['verification'] = rr
                r['verified'] = all(r[k] == rr[k] for k in ('status', 'steps', 'final_hash', 'transition_hash'))
            write(directory/(name+'-local-'+str(panel.index(f))+'.json'), r)
            return r
        out['local'][name] = pool(one, panel)
        rows = full_panel(p['tests'], v, cp, name, deadline, verify=True)
        out['full'][name] = dict(records=rows, summary=full_summary(rows))
        write(output, out)
    rows = full_panel(p['tests'], v, None, 'planner', deadline, verify=True, planner=True)
    out['full']['planner'] = dict(records=rows, summary=full_summary(rows))
    out['audit'] = audit(out)
    out['seconds'] = time.monotonic()-t
    out['execution_pass'] = out['audit']['pass'] and out['seconds'] <= p['budgets']['evaluate'] and all(
        full_valid(a['records']) for a in out['full'].values()) and all(r['status'] in ('clear', 'defeat') and r.get('verified', True)
        for records in out['local'].values() for r in records)
    local_boss_seeds = {f['seed'] for f in panel if f['reference_room_type'] == 'Boss' and f['mode'] == 'combat'}
    out['gates'] = {}
    base = out['full']['initial']['records']
    for name in actors:
        if name == 'initial':
            continue
        rows = out['full'][name]['records']
        bmap, cmap = {r['seed']: r for r in base}, {r['seed']: r for r in rows}
        count = lambda rs: sum(2 in r['acts_seen'] for r in rs)
        def local_clears(label, room):
            return sum(r['mode'] == 'combat' and r['reference_room_type'] == room and r['status'] == 'clear' for r in out['local'][label])
        gate = dict(boss_coverage=len(local_boss_seeds) >= 3,
            two_more_act2=count(rows) >= count(base)+2,
            difficulty_guard=all(count([r for r in rows if r['ascension'] == a]) >= count([r for r in base if r['ascension'] == a])-1 for a in range(11)),
            no_lost_full_win=all(cmap[s]['status'] == 'victory' for s, r in bmap.items() if r['status'] == 'victory'),
            local_no_regression=all(local_clears(name, room) >= local_clears('initial', room) for room in ROOMS))
        out['gates'][name] = {**gate, 'pass': all(gate.values())}
    out['expansion_gate'] = out['execution_pass'] and all(x['pass'] for x in out['gates'].values())
    write(output, out)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('plan', 'collect', 'bank', 'train', 'evaluate'))
    for key in ('plan', 'collection', 'bank', 'training', 'output'):
        p.add_argument('--'+key, type=Path, required=key == 'output')
    a = p.parse_args()
    for key, val in vars(a).items():
        if isinstance(val, Path):
            setattr(a, key, val.resolve())
    if a.output.exists():
        raise ValueError('Preserve previous attempt')
    torch.set_num_threads(1)
    v = {**manifest(), 'experiment': 'E153', 'torch': str(torch.__version__), 'numpy': np.__version__, 'device': 'cpu', 'encoder': ENCODER}
    if a.mode == 'plan':
        r = plan(v, a.output)
    elif a.mode == 'collect':
        r = collect(v, a.plan, a.output)
    elif a.mode == 'bank':
        r = build_bank(v, a.plan, a.collection, a.output)
    elif a.mode == 'train':
        r = train(v, a.plan, a.bank, a.output)
    else:
        r = evaluate(v, a.plan, a.bank, a.training, a.output)
    print(json.dumps({k: r[k] for k in ('execution_pass', 'train_coverage_pass', 'coverage', 'seconds', 'summary', 'gates', 'expansion_gate') if k in r}), flush=True)
