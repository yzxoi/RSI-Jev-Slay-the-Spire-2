#!/usr/bin/env python3
"""Fixed E133 data, certification, training and locked held-out evaluation."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.battle_search import compact
from rsi.checkpoints import file_hash
from rsi.ppo import ActorCritic, ENCODER_VERSION, HP, update
from rsi.ppo_env import episode
from rsi.research_restore import ENGINE_KEYS
from rsi.trace import digest
from rsi.training_bank import collect, certify, matched
from scripts.evaluate_battle_search_e120 import audit, manifest, write
from scripts.pilot_ppo_e125 import summarize, valid, paired_delta
from scripts.scale_ppo_e127 import attack_priority, load_checkpoint as load_e127

BANK = ROOT / 'experiments/E133/fixtures-v1.json'
COUNTS = {'train': 192, 'val': 24, 'test': 48}
LEARNERS = (1701, 1702)
CONFIGS = [dict(case=f'{split}-{i:03}', seed=f'e133_20261002_{split}_{i:03}',
                split=split, index=i, character='Ironclad', ascension=(0, 5, 10)[i % 3])
           for split, n in COUNTS.items() for i in range(n)]


def pool_map(fn, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fn, items))


def version():
    return {**manifest(), 'experiment': 'E133', 'encoder': ENCODER_VERSION,
            'hyperparameters': HP, 'torch': str(torch.__version__), 'numpy': str(np.__version__),
            'device': 'cpu', 'torch_threads': torch.get_num_threads(), 'engine_workers': 8,
            'learner_seeds': list(LEARNERS), 'scope': 'Ironclad A0/A5/A10 natural single battles'}


def read_committed(path, v):
    path = Path(path).resolve()
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(path.relative_to(ROOT))],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    r = json.loads(path.read_text())
    if any(r['manifest'][k] != v[k] for k in ENGINE_KEYS):
        raise ValueError('Frozen evidence engine changed')
    if not r['audit']['pass'] or not audit(r)['pass']:
        raise ValueError('Frozen evidence/raw trace audit failed')
    return r


def bank(v):
    b = read_committed(BANK, v)
    if b['configs'] != CONFIGS or not b['passed']:
        raise ValueError('Incomplete or changed preparation cohort')
    return b


def seed_entries(b, split):
    return [s['entries'] for s in b['seeds'] if s['split'] == split]


def training_pool(fs):
    """Deduplicate positions, never sample by policy outcome."""
    return [fs[i] for i in sorted({0, min(1, len(fs)-1), len(fs)-1})]


def training_entries(b, index):
    return [training_pool(fs)[(index-1+fs[0]['seed_index']) % len(training_pool(fs))]
            for fs in seed_entries(b, 'train')]


def panel_entries(b, split):
    return [(panel, fs[min(1, len(fs)-1)] if panel == 'early' else fs[-1])
            for panel in ('early', 'challenging') for fs in seed_entries(b, split)]


def eligible(b, testing=False):
    groups = [f for fs in seed_entries(b, 'train') for f in training_pool(fs)] if not testing else []
    groups += [f for _, f in panel_entries(b, 'test' if testing else 'val')]
    return list({f['case']: f for f in groups}.values())


def coverage(fs):
    return {'entries': len(fs), 'encounters': dict(Counter('/'.join(f['enemies']) for f in fs)),
            'room_types': dict(Counter(f['room_type'] for f in fs)),
            'ascensions': dict(Counter(str(f['ascension']) for f in fs)),
            'unique_deck_hashes': len({f['deck_hash'] for f in fs}),
            'hp_min_median_max': [min(f['hp'] for f in fs), statistics.median(f['hp'] for f in fs),
                                   max(f['hp'] for f in fs)] if fs else [],
            'with_potions': sum(bool(f['entry_potions']) for f in fs),
            'native_map_available': sum(f['native_map_available'] for f in fs)}


def freeze(v, output):
    start = time.monotonic()
    seeds = pool_map(lambda c: collect(c, v), CONFIGS)
    fixtures = [f for s in seeds for f in s['entries']]
    training = [f for s in seeds if s['split'] == 'train' and s['entries'] for f in training_pool(s['entries'])]
    report = dict(manifest=v, configs=CONFIGS, seeds=seeds, fixtures=fixtures,
                  seconds=time.monotonic()-start, coverage=coverage(training),
                  statuses=dict(Counter(s['status'] for s in seeds)))
    report['passed'] = (all(s['entries'] and s['status'] in ('ready', 'natural_defeat') for s in seeds)
                        and len(report['coverage']['encounters']) >= 8)
    report['audit'] = audit(report)
    write(output, report)
    print(json.dumps({k: report[k] for k in ('passed', 'seconds', 'coverage', 'statuses', 'audit')}), flush=True)


def certification(v, b, output, testing=False):
    directory = output.with_suffix('')
    directory.mkdir(exist_ok=False, parents=True)
    start = time.monotonic()
    deadline = start + (1800 if testing else max(0, 1800-b['seconds']))
    fs = eligible(b, testing)
    def run(f):
        r = certify(f, v, deadline)
        write(directory / f"{f['case']}.json", r)
        return r
    records = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for r in pool.map(run, fs):
            records.append(r)
            if len(records) % 16 == 0 or r['status'] != 'match':
                print(json.dumps({'phase': 'certification', 'done': len(records), 'total': len(fs),
                                  'case': r['case'], 'status': r['status'], 'error': r.get('error'),
                                  'seconds': time.monotonic()-start}), flush=True)
    report = dict(manifest=v, bank_sha256=file_hash(BANK), testing=testing,
                  cases=[f['case'] for f in fs], records=records, seconds=time.monotonic()-start,
                  passed=bool(records) and all(r['status'] == 'match' for r in records))
    report['audit'] = audit(report)
    report['passed'] &= report['audit']['pass']
    write(output, report)
    print(json.dumps({'phase': 'certificate_complete', 'passed': report['passed'],
                      'seconds': report['seconds'], 'audit': report['audit']}), flush=True)


def snapshots(path, v, b, testing=False):
    r = read_committed(path, v)
    fs = eligible(b, testing)
    if (not r['passed'] or r['testing'] != testing or r['bank_sha256'] != file_hash(BANK)
            or r['cases'] != [f['case'] for f in fs] or [q['case'] for q in r['records']] != r['cases']):
        raise ValueError('Incomplete/mismatched reset certificate')
    result = {}
    certificate_hash = file_hash(path)
    original = None
    if 'source_certificate' in r:
        from rsi.reset_fallback import PROTOCOL, recovery_valid
        source = r['source_certificate']
        if r.get('protocol')!=PROTOCOL or file_hash(source['path'])!=source['sha256']:
            raise ValueError('Unrecognized or edited recovery provenance')
        raw = read_committed(source['path'],v)
        if raw['cases']!=r['cases'] or raw['bank_sha256']!=r['bank_sha256'] or raw['testing']!=testing:
            raise ValueError('Recovery belongs to another cohort')
        original = {q['case']:q for q in raw['records']}
    for f, q in zip(fs, r['records']):
        recovered = q.get('restore_reason')=='verified_full_prefix_recovery'
        if recovered:
            if (original is None or q.get('original_native_failure')!=original[f['case']]
                    or not recovery_valid(q)):
                raise ValueError('Full-prefix recovery proof is missing or invalid')
        elif original is not None and q!=original[f['case']]:
            raise ValueError('Previously passing certificate was changed')
        if q['status'] != 'match' or q['native'] != (f['native_map_available'] and not recovered):
            raise ValueError('Uncertified restore mode')
        s = q.get('snapshot')
        if q['native'] and (not s or file_hash(ROOT/s['path']) != s['sha256']
                            or s['entry_hash'] != f['entry_hash'] or s['prefix_hash'] != f['prefix_hash']
                            or s['map_hash'] != f['map_hash'] or s['engine'] != {k:v[k] for k in ENGINE_KEYS}):
            raise ValueError('Edited/unbound native snapshot')
        result[f['case']] = {**s, 'certificate_sha256': certificate_hash} if s else None
    return result


def evaluations_summary(records):
    panels = {panel: summarize([r for r in records if r['panel'] == panel]) for panel in ('early', 'challenging')}
    return dict(summary=summarize(records), panels=panels,
                by_difficulty={f'{panel}:A{asc}': summarize([r for r in records if r['panel']==panel and r['ascension']==asc])
                               for panel in panels for asc in (0,5,10)})


def evaluate(fs, v, label, snaps, model=None, policy=None, verify=False):
    def run(item):
        panel, f = item
        r, data = episode(f, v, label, model=model, policy=policy, checkpoint=snaps[f['case']])
        r.update(panel=panel, ascension=f['ascension'], seed=f['seed'], room_type=f['room_type'])
        if data and 'reward' in r:
            predictions = np.asarray([d['value'] for d in data])
            r['value_calibration'] = dict(n=len(data), mse=float(np.mean((predictions-r['reward'])**2)),
                                         mean_prediction=float(predictions.mean()), actual_return=r['reward'])
        if verify and r['status'] in ('clear', 'defeat'):
            replay, _ = episode(f, v, label+':independent_full_prefix', expected=r['plan'])
            r['verification'] = compact(replay)
            r['verification_match'] = matched(r, replay)
        return compact(r)
    records = pool_map(run, fs)
    return dict(label=label, records=records, **evaluations_summary(records),
                passed=valid(records) and (not verify or all(r.get('verification_match') for r in records)))


def save_model(path, model, optimizer, v, learner, index):
    torch.save(dict(model=model.state_dict(), optimizer=optimizer.state_dict(), config=model.config,
                    manifest=v, bank_sha256=file_hash(BANK), learner=learner, update=index), path)
    return dict(path=str(path.relative_to(ROOT)), sha256=file_hash(path), update=index, config=model.config)


def load_model(cp, v):
    path = ROOT/cp['path']
    if file_hash(path) != cp['sha256']:
        raise ValueError('Changed model checkpoint')
    data = torch.load(path, map_location='cpu', weights_only=True)
    if (data['bank_sha256'] != file_hash(BANK) or data['manifest']['encoder'] != ENCODER_VERSION
            or any(data['manifest'][k] != v[k] for k in ENGINE_KEYS)):
        raise ValueError('Model bank/encoder/engine mismatch')
    model = ActorCritic(**data['config'])
    model.load_state_dict(data['model'])
    model.eval()
    return model


def selection_score(validation):
    c, e = validation['panels']['challenging'], validation['panels']['early']
    return c['clears'], c['mean_reward'], e['clears'], e['mean_reward'], -validation['update']


def train(v, b, output, certificate):
    snaps = snapshots(certificate, v, b)
    directory = output.with_suffix('')
    directory.mkdir(exist_ok=False, parents=True)
    report = dict(manifest=v, bank_sha256=file_hash(BANK), certificate_sha256=file_hash(certificate),
                  learners=[], passed=True)
    for learner in LEARNERS:
        started = time.monotonic()
        work = 0.
        torch.manual_seed(learner)
        rng = np.random.default_rng(learner)
        model = ActorCritic()
        optimizer = torch.optim.Adam(model.parameters(), lr=HP['lr'], eps=1e-5)
        row = dict(size='S', learner=learner, parameters=sum(p.numel() for p in model.parameters()),
                   updates=[], validations=[], checkpoints=[], status='running')
        report['learners'].append(row)
        cp = save_model(directory/f'S-{learner}-00.pt', model, optimizer, v, learner, 0)
        row['checkpoints'].append(cp)
        val = evaluate(panel_entries(b, 'val'), {**v, 'checkpoint': cp}, f'{learner}:val:0', snaps, model=model)
        val['update'] = 0
        row['validations'].append(val)
        print(json.dumps({'learner':learner, 'validation':0, 'panels':val['panels']}), flush=True)
        for index in range(1,33):
            if work >= 3600:
                row['status'] = 'time_cap'
                break
            start = time.monotonic()
            remaining = 3600-work
            work_deadline = start+remaining
            def run(f):
                left = work_deadline-time.monotonic()
                if left <= 0:
                    return (dict(case=f['case'],status='unstarted',steps=0,seconds=0,
                                 entry_verified=False,illegal_actions=0,reason='Learner work deadline'), [])
                sample = int(digest([learner,index,f['case']])[:16],16)
                return episode(f, {**v, 'checkpoint':cp}, f'{learner}:train:{index}', model=model,
                               sample_seed=sample, checkpoint=snaps[f['case']], seconds=min(30,left))
            batch = pool_map(run, training_entries(b,index))
            records = [compact(r) for r,_ in batch]
            step = dict(update=index, episodes=records, summary=summarize(records))
            if not valid(records):
                step['optimizer_skipped'] = True
                row['updates'].append(step)
                row['status'] = 'invalid'
                work += time.monotonic()-start
                print(json.dumps({'learner':learner,'update':index,'status':'invalid', 'summary':step['summary']}),flush=True)
                break
            opt = time.monotonic()
            try:
                step['optimization'] = update(model,optimizer,[(d,r['reward']) for r,d in batch],rng)
            except Exception as exc:
                step['optimizer_error'] = f'{type(exc).__name__}: {exc}'
                row['updates'].append(step)
                row['status'] = 'invalid'
                work += time.monotonic()-start
                break
            step['optimization_seconds'] = time.monotonic()-opt
            step['collection_and_optimization_seconds'] = time.monotonic()-start
            step['median_restore_seconds'] = statistics.median(r['replay_seconds'] for r in records)
            work += step['collection_and_optimization_seconds']
            row['updates'].append(step)
            cp = save_model(directory/f'S-{learner}-{index:02}.pt', model,optimizer,v,learner,index)
            row['checkpoints'].append(cp)
            print(json.dumps({'learner':learner,'update':index,'work_seconds':work,
                              'summary':step['summary'],'optimization':step['optimization']}),flush=True)
            if index % 8 == 0:
                val = evaluate(panel_entries(b,'val'),{**v,'checkpoint':cp},f'{learner}:val:{index}',snaps,model=model)
                val['update'] = index
                row['validations'].append(val)
                print(json.dumps({'learner':learner,'validation':index,'panels':val['panels']}),flush=True)
            write(directory/f'S-{learner}.json',row)
        else:
            row['status'] = 'complete'
        for name, limit in [('short',8),('long',32)]:
            vals = [q for q in row['validations'] if q['passed'] and q['update']<=limit]
            if vals:
                best = max(vals,key=selection_score)
                row[name+'_selected'] = next(c for c in row['checkpoints'] if c['update']==best['update'])
        row.update(selected=row.get('long_selected'), work_seconds=work, seconds=time.monotonic()-started)
        report['passed'] &= row['status']=='complete' and bool(row.get('short_selected')) and bool(row.get('long_selected'))
        write(directory/f'S-{learner}.json',row)
    report['audit'] = audit(report)
    report['passed'] &= report['audit']['pass']
    write(output,report)
    print(json.dumps({'phase':'training_complete','passed':report['passed'],'audit':report['audit'],
                      'selected':[{k:r.get(k) for k in ('learner','status','short_selected','long_selected')} for r in report['learners']]}),flush=True)


def locked_training(path,v):
    t = read_committed(path,v)
    if (not t['passed'] or t['bank_sha256']!=file_hash(BANK)
            or [r['learner'] for r in t['learners']]!=list(LEARNERS)):
        raise ValueError('Both complete learners and committed selections required')
    for r in t['learners']:
        for cp in r['checkpoints']:
            if file_hash(ROOT/cp['path'])!=cp['sha256']:
                raise ValueError('Training checkpoint changed')
    return t


def subset(arm,panel,ascension=None):
    rows = [r for r in arm['records'] if r['panel']==panel and (ascension is None or r['ascension']==ascension)]
    return dict(records=rows,summary=summarize(rows),passed=valid(rows))


def compare(a,b,panel,ascension=None):
    aa,bb = subset(a,panel,ascension),subset(b,panel,ascension)
    return paired_delta(aa,bb) if aa['passed'] and bb['passed'] else None


def test(v,b,output,training,certificate):
    t = locked_training(training,v)
    snaps = snapshots(certificate,v,b,True)
    directory = output.with_suffix('')
    directory.mkdir(exist_ok=False,parents=True)
    report = dict(manifest=v,bank_sha256=file_hash(BANK),training_sha256=file_hash(training),
                  certificate_sha256=file_hash(certificate),arms={})
    old = json.loads((ROOT/'experiments/E127/training-v1.json').read_text())
    arms = [('planner',None,None,None),('attack_priority',None,attack_priority,None)]
    for row in old['learners']:
        if row['size']=='S':
            arms.append((f"E127-{row['learner']}",load_e127(row['selected'],v),None,None))
    for row in t['learners']:
        for budget in ('short','long'):
            cp = row[budget+'_selected']
            arms.append((f"{budget}-{row['learner']}",load_model(cp,v),None,cp))
    cache = {}
    start = time.monotonic()
    for name,model,policy,cp in arms:
        if cp and cp['sha256'] in cache:
            source = cache[cp['sha256']]
            result = {**report['arms'][source], 'label':name, 'alias_of':source}
        else:
            result = evaluate(panel_entries(b,'test'),{**v,'checkpoint':cp},name,snaps,
                              model=model,policy=policy,verify=cp is not None)
            if cp:
                cache[cp['sha256']] = name
        report['arms'][name] = result
        write(directory/f'{name}.json',result)
        print(json.dumps({'phase':'test','arm':name,'panels':result['panels'],
                          'passed':result['passed'],'alias_of':result.get('alias_of')}),flush=True)
    report['comparisons'] = {}
    practical,longer = [],[]
    for learner in LEARNERS:
        new = report['arms'][f'long-{learner}']
        for name in (f'E127-{learner}',f'short-{learner}','planner','attack_priority'):
            old = report['arms'][name]
            report['comparisons'][f'long-{learner}_vs_{name}'] = {
                'challenging':compare(new,old,'challenging'), 'early':compare(new,old,'early'),
                'early_A0':compare(new,old,'early',0)}
        c = report['comparisons'][f'long-{learner}_vs_E127-{learner}']
        p = report['comparisons'][f'long-{learner}_vs_planner']['challenging']
        practical.append(bool(c['challenging'] and c['early_A0'] and p and
                              c['challenging']['clear_delta']>=3 and c['challenging']['median_hp_delta']>=2 and
                              c['early_A0']['clear_delta']>=0 and c['early_A0']['median_hp_delta']>=-2 and p['clear_delta']>=0))
        c = report['comparisons'][f'long-{learner}_vs_short-{learner}']
        longer.append(bool(c['challenging'] and c['early'] and c['challenging']['clear_delta']>=2 and
                           c['challenging']['median_hp_delta']>=2 and c['early']['clear_delta']>=0))
    report['execution_pass'] = all(a['passed'] for a in report['arms'].values())
    report['audit'] = audit(report)
    report['execution_pass'] &= report['audit']['pass']
    report['practical_improvement_pass'] = report['execution_pass'] and all(practical)
    report['longer_training_pass'] = report['execution_pass'] and all(longer)
    report['seconds'] = time.monotonic()-start
    write(output,report)
    print(json.dumps({k:report[k] for k in ('execution_pass','practical_improvement_pass','longer_training_pass','audit','seconds')}),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=('freeze','certify_train','train','certify_test','test'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--certificate')
    parser.add_argument('--training')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError('Do not overwrite previous evidence')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    v = version()
    if args.phase=='freeze':
        freeze(v,output)
    else:
        b = bank(v)
        if args.phase=='certify_train':
            certification(v,b,output)
        elif args.phase=='train':
            train(v,b,output,args.certificate)
        elif args.phase=='certify_test':
            locked_training(args.training,v)
            certification(v,b,output,True)
        else:
            test(v,b,output,args.training,args.certificate)


if __name__=='__main__':
    main()
