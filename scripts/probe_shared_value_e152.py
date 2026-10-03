#!/usr/bin/env python3
"""Matched E152 critic encoders, frozen weights, then fresh-seed evaluation."""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.checkpoints import file_hash, wire_pairs
from rsi.phase_rl import controller, phase_encode
from rsi.run_env import run, replay
from rsi.shared_value import ENCODER, shared_encode, ValueMLP
from rsi.task_value import Progress, PHASES, task_features, balanced_weights, metrics, ridge_features, ridge_fit
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import manifest, write, audit
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.pilot_onpolicy_e146 import reward
from scripts.probe_task_value_e148 import checked, load_data

SETTINGS = dict(epochs=24, lr=3e-4, batch=512, grad_norm=1., workers=8,
    prepare_budget=180, fit_budget=180, collect_budget=450, score_budget=120,
    learners=[2201, 2202], arms=['hash', 'shared'], ridge_alpha=.01)


def configs():
    return [dict(case=f'test-A{a}-{i:03}-r{r}', seed=f'e152_test_Ironclad_A{a}_{i:03}',
        character='Ironclad', ascension=a, index=i, repetition=r, split='test', arm='neural_all',
        sample_seed=152000000+a*10000+i*10+r)
        for a in (0, 5, 10) for i in range(24) for r in range(2)]


def info(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=file_hash(path))


def arrays(meta):
    path = ROOT / meta['path']
    if file_hash(path) != meta['sha256']:
        raise ValueError('Changed frozen arrays')
    return dict(np.load(path))


def plan(v, output):
    source = ROOT / 'experiments/E148/bank-v2.json'
    bank = checked(source)
    original = ROOT / 'experiments/E148/training-v1.json'
    models = [m for m in checked(original)['models'] if m['arm'] == 'task']
    out = dict(manifest=v, settings=SETTINGS, configs=configs(), source_bank=info(source),
        source_training=info(original), behavior=bank['behavior'], old_critics=models,
        final_acceptance_seeds_unused=True)
    load_phase(out['behavior'])
    write(output, out)
    return out


def frozen(path):
    p = checked(path)
    if p['settings'] != SETTINGS or p['configs'] != configs():
        raise ValueError('Protocol drift')
    return p


def prepare(v, plan_path, output):
    t = time.monotonic()
    p = frozen(plan_path)
    source = ROOT / p['source_bank']['path']
    if file_hash(source) != p['source_bank']['sha256']:
        raise ValueError('Changed E148 source')
    bank = checked(source)
    data = load_data(bank)
    selected = [i for i, r in enumerate(bank['records']) if r['split'] == 'train']
    if selected != list(range(432)):
        raise ValueError('TRAIN scope changed')
    shared = []
    for i in selected:
        if time.monotonic() - t > SETTINGS['prepare_budget']:
            raise TimeoutError('Prepare budget')
        r = bank['records'][i]
        path = ROOT / r['trace_path']
        wire = path.with_name('wire.jsonl')
        if file_hash(path) != r['trace_sha256'] or file_hash(wire) != r['wire.jsonl_sha256']:
            raise ValueError('Source raw hash changed')
        pairs = wire_pairs(wire)
        events = [x['data'] for line in path.read_text().splitlines() if (x := json.loads(line))['kind'] == 'decision']
        positions = np.flatnonzero(data['case_ids'] == i)
        if len(events) != len(positions) or len(pairs) != len(events)+1:
            raise ValueError('Incomplete TRAIN alignment')
        observer = Progress(r['ascension'])
        for j, e in enumerate(events):
            state = pairs[j][1]
            if e['before'] != digest(state) or pairs[j+1][0] != e['chosen']['action']:
                raise ValueError('Source wire/action mismatch')
            if not np.array_equal(task_features(observer.observe(state)), data['tasks'][positions[j]]):
                raise ValueError('Source task mismatch')
            shared.append(shared_encode(state, data['states'][positions[j]]))
    mask = np.isin(data['case_ids'], selected)
    d = {key: value[mask] for key, value in data.items()}
    d['shared'] = np.stack(shared)
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / 'tensors.npz'
    np.savez_compressed(target, **d)
    out = dict(manifest=v, plan_sha256=file_hash(plan_path), source_bank=p['source_bank'],
        selected_case_ids=selected, tensors=info(target), rows=len(shared), paths=432, game_seeds=216,
        train_only=True, raw_files_verified=864, seconds=time.monotonic()-t,
        execution_pass=time.monotonic()-t <= SETTINGS['prepare_budget'])
    write(output, out)
    return out


def fit(v, plan_path, prepared_path, output):
    t = time.monotonic()
    p, prepared = frozen(plan_path), checked(prepared_path)
    if not prepared['execution_pass'] or prepared['plan_sha256'] != file_hash(plan_path):
        raise ValueError('Unfrozen TRAIN input')
    d = arrays(prepared['tensors'])
    x = {arm: torch.from_numpy(np.concatenate([d[key], d['tasks']], axis=1))
         for arm, key in (('hash', 'states'), ('shared', 'shared'))}
    y = torch.from_numpy(d['targets'])
    w = torch.from_numpy(balanced_weights(d['case_ids']))
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)
    result = dict(manifest=v, settings=SETTINGS, plan_sha256=file_hash(plan_path),
        prepared_sha256=file_hash(prepared_path), behavior=p['behavior'], old_critics=p['old_critics'],
        models=[], train_paths=432, train_seeds=216, train_rows=len(y), dev_test_fit_rows=0)
    for learner in SETTINGS['learners']:
        torch.manual_seed(learner)
        initial = ValueMLP()
        models = {arm: copy.deepcopy(initial) for arm in SETTINGS['arms']}
        opts = {arm: torch.optim.Adam(m.parameters(), lr=SETTINGS['lr']) for arm, m in models.items()}
        curves = {arm: [] for arm in SETTINGS['arms']}
        rng = np.random.default_rng(learner)
        for epoch in range(SETTINGS['epochs']):
            order = rng.permutation(len(y))
            for off in range(0, len(y), SETTINGS['batch']):
                if time.monotonic()-t > SETTINGS['fit_budget']:
                    raise TimeoutError('Fit budget')
                ix = order[off:off+SETTINGS['batch']]
                for arm, m in models.items():
                    loss = (w[ix] * (m(x[arm][ix])-y[ix]).square()).mean()
                    if not torch.isfinite(loss):
                        raise ValueError('Nonfinite loss')
                    opts[arm].zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(m.parameters(), SETTINGS['grad_norm'], error_if_nonfinite=True)
                    opts[arm].step()
            with torch.inference_mode():
                for arm, m in models.items():
                    curves[arm].append(dict(epoch=epoch+1, mse=float((w*(m(x[arm])-y).square()).mean())))
            print(json.dumps(dict(learner=learner, epoch=epoch+1,
                mse={a: c[-1]['mse'] for a, c in curves.items()})), flush=True)
        for arm, m in models.items():
            path = directory / f'{learner}-{arm}.pt'
            torch.save(dict(model=m.state_dict(), manifest=v, learner=learner, arm=arm), path)
            result['models'].append(dict(**info(path), learner=learner, arm=arm,
                parameters=sum(z.numel() for z in m.parameters()), curve=curves[arm]))
    result['baselines'] = dict(constant=float((w*y).mean()),
        ridge=ridge_fit(ridge_features(d['states'], d['tasks'], d['phases']),
                        d['targets'], d['case_ids']).tolist())
    result['actor_unchanged'] = file_hash(ROOT/p['behavior']['path']) == p['behavior']['sha256']
    result['seconds'] = time.monotonic()-t
    result['execution_pass'] = result['actor_unchanged'] and result['seconds'] <= SETTINGS['fit_budget']
    write(output, result)
    return result


def collect(v, plan_path, training_path, output):
    p, training = frozen(plan_path), checked(training_path)
    if not training['execution_pass'] or training['plan_sha256'] != file_hash(plan_path):
        raise ValueError('Unfrozen weights before fresh collection')
    for cp in training['models']:
        if file_hash(ROOT/cp['path']) != cp['sha256']:
            raise ValueError('Changed frozen weights')
    model = load_phase(p['behavior'])
    t = time.monotonic()
    deadline = t+SETTINGS['collect_budget']
    directory = output.with_suffix('')
    directory.mkdir(parents=True, exist_ok=False)

    def one(config):
        observer, temporary, rows = Progress(config['ascension']), [], []
        base = controller(model, config['sample_seed'], temporary)

        def choose(state, choices, previous):
            context = observer.observe(state)
            chosen, extra = base(state, choices, previous)
            old = temporary.pop()['encoded'][0]
            rows.append((old, shared_encode(state, old), task_features(context), PHASES.index(state['decision'])))
            extra['value_task_context'] = context
            return chosen, extra

        record = run(config, {**v, 'behavior_checkpoint': p['behavior']}, controller=choose,
                     stop_after_battles=6, seconds=min(180, max(.001, deadline-time.monotonic())))
        if config['index'] == 0 and config['repetition'] == 0 and record['status'] in ('defeat', 'curriculum_clear'):
            record['verification'] = replay(record, v, seconds=min(180, max(.001, deadline-time.monotonic())))
        write(directory/(config['case']+'.json'), record)
        print(json.dumps({k: record[k] for k in ('case', 'status', 'steps', 'completed_battles')}), flush=True)
        return record, rows

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, p['configs']))
    records = [r for r, _ in results]
    raw = audit(records)
    complete = raw['pass'] and all(r['status'] in ('defeat', 'curriculum_clear') and
        r['steps'] == len(rows) == r['network_calls'] and r['planner_calls'] == 0 and
        r.get('verification', {}).get('status', 'match') == 'match' for r, rows in results)
    out = dict(manifest=v, plan_sha256=file_hash(plan_path), training_sha256=file_hash(training_path),
        records=records, audit=raw, behavior=p['behavior'], final_acceptance_seeds_unused=True)
    if complete:
        data = {k: [] for k in ('states', 'shared', 'tasks', 'phases', 'case_ids', 'targets')}
        for i, (r, rows) in enumerate(results):
            for old, shared, task, phase in rows:
                for key, val in zip(data, (old, shared, task, phase, i, reward(r))):
                    data[key].append(val)
        data = {key: np.asarray(value, dtype=np.int32 if key in ('phases', 'case_ids') else np.float32)
                for key, value in data.items()}
        target = directory/'tensors.npz'
        np.savez_compressed(target, **data)
        out['tensors'] = info(target)
        # Rebuild all preselected replay paths independently from original wires.
        out['reconstruction'] = []
        for i, r in enumerate(records):
            if r['index'] or r['repetition']:
                continue
            path = ROOT/r['trace_path']
            pairs = wire_pairs(path.with_name('wire.jsonl'))
            events = [x['data'] for line in path.read_text().splitlines() if (x := json.loads(line))['kind'] == 'decision']
            positions = np.flatnonzero(data['case_ids'] == i)
            observer, previous = Progress(r['ascension']), None
            for j, e in enumerate(events):
                state = pairs[j][1]
                if e['before'] != digest(state) or pairs[j+1][0] != e['chosen']['action']:
                    raise ValueError('Fresh trace alignment failure')
                old = phase_encode(state, e['candidates'], previous, max_actions=4096)[0]
                expected = dict(states=old, shared=shared_encode(state, old), tasks=task_features(observer.observe(state)))
                if any(not np.array_equal(data[k][positions[j]], value) for k, value in expected.items()):
                    raise ValueError('Fresh encoded reconstruction failure')
                previous = e['chosen']
            out['reconstruction'].append(dict(case=r['case'], rows=len(events), exact=True))
    out['seconds'] = time.monotonic()-t
    out['execution_pass'] = complete and out['seconds'] <= SETTINGS['collect_budget']
    write(output, out)
    return out


def score(v, plan_path, training_path, bank_path, output):
    t = time.monotonic()
    p, training, bank = frozen(plan_path), checked(training_path), checked(bank_path)
    if not bank['execution_pass'] or bank['training_sha256'] != file_hash(training_path):
        raise ValueError('Incomplete or unfrozen fresh bank')
    if [dict((k, r[k]) for k in c) for c, r in zip(p['configs'], bank['records'])] != p['configs']:
        raise ValueError('Fresh cohort mismatch')
    d = arrays(bank['tensors'])
    y, ids = d['targets'], d['case_ids']
    preds = dict(constant=np.full(len(y), training['baselines']['constant']),
        progress_ridge=ridge_features(d['states'], d['tasks'], d['phases']) @ training['baselines']['ridge'])
    cps = [(f"{cp['learner']}-{cp['arm']}", cp, cp['arm']) for cp in training['models']]
    cps += [(f"e148-{cp['learner']}", cp, 'hash') for cp in p['old_critics']]
    for name, cp, arm in cps:
        if file_hash(ROOT/cp['path']) != cp['sha256']:
            raise ValueError('Changed final critic weights')
        m = ValueMLP()
        m.load_state_dict(torch.load(ROOT/cp['path'], map_location='cpu', weights_only=True)['model'])
        m.eval()
        x = np.concatenate([d['shared' if arm == 'shared' else 'states'], d['tasks']], 1)
        with torch.inference_mode():
            preds[name] = m(torch.from_numpy(x)).numpy()
    goal = d['tasks'][:, 2] == 1
    groups = dict(all=np.ones(len(y), dtype=bool), post_six=goal, pre_six=~goal)
    groups.update({f'A{a}': np.isclose(d['tasks'][:, 4], a/10) for a in (0, 5, 10)})
    groups.update({f'phase:{ph}': d['phases'] == i for i, ph in enumerate(PHASES)})
    out = dict(manifest=v, plan_sha256=file_hash(plan_path), training_sha256=file_hash(training_path),
        bank_sha256=file_hash(bank_path), metrics={n: {g: metrics(pred[m], y[m], ids[m]) for g, m in groups.items()}
            for n, pred in preds.items()}, cases=[], paired={}, gates={}, final_acceptance_seeds_unused=True)
    for i, r in enumerate(bank['records']):
        m = ids == i
        out['cases'].append(dict(case=r['case'], seed=r['seed'], ascension=r['ascension'], status=r['status'],
            steps=r['steps'], trace_sha256=r['trace_sha256'], mse={n: metrics(pred[m], y[m], ids[m])['mse'] for n, pred in preds.items()}))
    seeds = sorted({r['seed'] for r in out['cases']})
    draws = np.random.default_rng(152).integers(len(seeds), size=(2000, len(seeds)))
    best = min(('constant', 'progress_ridge'), key=lambda n: out['metrics'][n]['all']['mse'])
    boundary_seeds = {bank['records'][i]['seed'] for i in np.unique(ids[goal])}
    for learner, old in zip(SETTINGS['learners'], (2101, 2102)):
        name, control = f'{learner}-shared', f'{learner}-hash'
        candidate, base = out['metrics'][name], out['metrics'][control]
        intervals = {}
        for other in (control, best):
            delta = np.array([np.mean([r['mse'][name]-r['mse'][other] for r in out['cases'] if r['seed'] == s]) for s in seeds])
            ci = np.quantile(delta[draws].mean(axis=1), [.025, .975]).tolist()
            intervals[other] = dict(mean_delta=float(delta.mean()), bootstrap95=ci)
        out['paired'][name] = intervals
        gate = dict(ten_percent_vs_hash=candidate['all']['mse'] <= .9*base['all']['mse'],
            five_percent_vs_simple=candidate['all']['mse'] <= .95*out['metrics'][best]['all']['mse'],
            not_worse_than_old_task=candidate['all']['mse'] <= out['metrics'][f'e148-{old}']['all']['mse'],
            ci_below_hash_and_simple=all(x['bootstrap95'][1] < 0 for x in intervals.values()),
            difficulty_guard=all(candidate[f'A{a}']['mse'] <= 1.1*base[f'A{a}']['mse'] for a in (0, 5, 10)),
            boundary_coverage=len(boundary_seeds) >= 10,
            boundary_calibration=bool(candidate['post_six']['n'] and candidate['post_six']['mae'] <= .25))
        out['gates'][name] = {**gate, 'pass': all(gate.values())}
    target = output.with_suffix('.npz')
    np.savez_compressed(target, case_ids=ids, targets=y, **preds)
    out['predictions'] = info(target)
    out['coverage'] = dict(paths=len(bank['records']), game_seeds=len(seeds), decisions=len(y),
        post_six_decisions=int(goal.sum()), post_six_game_seeds=len(boundary_seeds),
        outcomes={f'A{a}': {status: sum(r['ascension'] == a and r['status'] == status for r in bank['records'])
                           for status in ('curriculum_clear', 'defeat')} for a in (0, 5, 10)})
    out['seconds'] = time.monotonic()-t
    out['execution_pass'] = len(seeds) == 72 and len(bank['records']) == 144 and out['seconds'] <= SETTINGS['score_budget']
    out['expansion_gate'] = out['execution_pass'] and all(g['pass'] for g in out['gates'].values())
    write(output, out)
    return out


def plot(training_path, evaluation_path, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    train, ev = [json.loads(p.read_text()) for p in (training_path, evaluation_path)]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
    colors = {'hash': '#c56b42', 'shared': '#137c8b'}
    for cp in train['models']:
        ax[0].plot([x['epoch'] for x in cp['curve']], [x['mse'] for x in cp['curve']],
            color=colors[cp['arm']], linestyle='-' if cp['learner'] == 2201 else '--',
            label=f"{cp['learner']} {cp['arm']}")
    ax[0].set(title='TRAIN: equal-path MSE', xlabel='Fixed epoch', ylabel='MSE')
    ax[0].legend(fontsize=8)
    names = ['constant', 'progress_ridge', 'e148-2101', 'e148-2102', '2201-hash', '2201-shared', '2202-hash', '2202-shared']
    ax[1].barh(names, [ev['metrics'][n]['all']['mse'] for n in names],
        color=[colors['shared'] if 'shared' in n else '#9aa5ab' for n in names])
    ax[1].invert_yaxis()
    ax[1].set(title='Fresh TEST: 72 game seeds / 144 paths', xlabel='Equal-path MSE (lower is better)')
    ax[2].barh(names, [ev['metrics'][n]['post_six'].get('mae', float('nan')) for n in names],
        color=[colors['shared'] if 'shared' in n else '#9aa5ab' for n in names])
    ax[2].invert_yaxis()
    ax[2].axvline(.25, color='black', linestyle=':', label='Gate: 0.25')
    ax[2].set(title='After six clears: calibration', xlabel='MAE (lower is better)')
    ax[2].legend(fontsize=8)
    fig.suptitle('E152 — Shared attributes versus identity-path hashing; frozen behavior policy', fontsize=12)
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ('png', 'svg'):
        fig.savefig(output/f'shared-value.{suffix}', dpi=160)
    plt.close(fig)
    return {'plot': str(output)}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('plan', 'prepare', 'fit', 'collect', 'score', 'plot'))
    for key in ('plan', 'prepared', 'training', 'bank', 'evaluation', 'output'):
        p.add_argument('--'+key, type=Path, required=key == 'output')
    a = p.parse_args()
    for k, val in vars(a).items():
        if isinstance(val, Path):
            setattr(a, k, val.resolve())
    if a.output.exists():
        raise ValueError('Preserve previous attempt')
    torch.set_num_threads(1)
    v = {**manifest(), 'experiment': 'E152', 'encoder': ENCODER,
         'torch': str(torch.__version__), 'numpy': np.__version__, 'device': 'cpu'}
    if a.mode == 'plan':
        out = plan(v, a.output)
    elif a.mode == 'prepare':
        out = prepare(v, a.plan, a.output)
    elif a.mode == 'fit':
        out = fit(v, a.plan, a.prepared, a.output)
    elif a.mode == 'collect':
        out = collect(v, a.plan, a.training, a.output)
    elif a.mode == 'score':
        out = score(v, a.plan, a.training, a.bank, a.output)
    else:
        out = plot(a.training, a.evaluation, a.output)
    print(json.dumps({k: out[k] for k in ('seconds', 'execution_pass', 'coverage', 'gates', 'expansion_gate', 'plot') if k in out}), flush=True)
