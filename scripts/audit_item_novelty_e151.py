#!/usr/bin/env python3
"""Read-only E148 identity coverage audit; no training, inference or engine calls."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rsi.checkpoints import file_hash, wire_pairs
from rsi.task_value import balanced_weights
from rsi.trace import digest

KINDS = ('card', 'potion', 'relic')


def identity(kind, obj):
    if not isinstance(obj, dict) or not (obj.get('id') or obj.get('name')):
        raise ValueError(f'Missing {kind} identity: {obj}')
    # Upgrades remain part of the same base identity; inventory keeps the flag.
    name = re.sub(r'\+\d*$', '', obj.get('name', '')).strip()
    return kind, obj.get('id', ''), name


def extract(state):
    p = state.get('player') or {}
    owned, visible, inventory = set(), set(), []
    for kind, field in zip(KINDS, ('deck', 'potions', 'relics')):
        for obj in p.get(field) or []:
            item = identity(kind, obj)
            owned.add(item)
            inventory.append((item, bool(obj.get('upgraded', False))))
    owned.update(identity('card', obj) for obj in state.get('hand') or [])
    visible.update(owned)
    for kind, field in zip(KINDS, ('cards', 'potions', 'relics')):
        visible.update(identity(kind, obj) for obj in state.get(field) or [])
    if state.get('potion'):
        visible.add(identity('potion', state['potion']))
    for bundle in state.get('bundles') or []:
        visible.update(identity('card', obj) for obj in bundle.get('cards') or [])
    return owned, visible, inventory


def aliases(items):
    names = defaultdict(set)
    for kind, ident, name in items:
        if name:
            names[kind, name].update([ident] if ident else [])
    if any(len(ids) > 1 for ids in names.values()):
        raise ValueError('Ambiguous TRAIN identity names')
    return {key: 'id:' + next(iter(ids)) if ids else 'name:' + key[1]
            for key, ids in names.items()}


def canonical(item, lookup):
    kind, ident, name = item
    key = lookup.get((kind, name))
    if key and ident and key.startswith('id:') and key != 'id:' + ident:
        raise ValueError('Conflicting DEV name and TRAIN ID')
    return kind, key or ('id:' + ident if ident else 'name:' + name)


def main(output):
    start = time.monotonic()
    bank_path = ROOT / 'experiments/E148/bank-v2.json'
    eval_path = ROOT / 'experiments/E148/evaluation-v1.json'
    bank, ev = [json.loads(p.read_text()) for p in (bank_path, eval_path)]
    if file_hash(bank_path) != ev['bank_sha256']:
        raise ValueError('Changed bank')
    for meta in (bank['tensors'], ev['predictions']):
        if file_hash(ROOT / meta['path']) != meta['sha256']:
            raise ValueError('Changed frozen arrays')
    data = dict(np.load(ROOT / bank['tensors']['path']))
    pred = dict(np.load(ROOT / ev['predictions']['path']))
    records, rows, train_items = bank['records'], [], set()
    for i, rec in enumerate(records):
        if time.monotonic() - start > 180:
            raise TimeoutError('Registered read-only budget')
        path = ROOT / rec['trace_path']
        wire = path.with_name('wire.jsonl')
        if file_hash(path) != rec['trace_sha256'] or file_hash(wire) != rec['wire.jsonl_sha256']:
            raise ValueError('Changed original trace')
        pairs = wire_pairs(wire)
        events = [x['data'] for line in path.read_text().splitlines()
                  if (x := json.loads(line))['kind'] == 'decision']
        positions = np.flatnonzero(data['case_ids'] == i)
        if len(events) != len(positions) or len(events) != rec['steps'] or len(pairs) != len(events) + 1:
            raise ValueError('Incomplete original path')
        for j, event in enumerate(events):
            state = pairs[j][1]
            if event['before'] != digest(state) or pairs[j + 1][0] != event['chosen']['action']:
                raise ValueError('Wire/action alignment failure')
            if positions[j] != len(rows):
                raise ValueError('Changed tensor ordering')
            owned, visible, inv = extract(state)
            rows.append((owned, visible, inv))
            if rec['split'] == 'train':
                train_items.update(visible)
    lookup = aliases(train_items)
    rows = [(set(canonical(x, lookup) for x in own),
             set(canonical(x, lookup) for x in vis),
             tuple(sorted((canonical(x, lookup), up) for x, up in inv)))
            for own, vis, inv in rows]
    train_mask = np.array([records[i]['split'] == 'train' for i in data['case_ids']])
    dev_idx = np.flatnonzero(~train_mask)
    ids, targets = data['case_ids'][dev_idx], data['targets'][dev_idx]
    if not np.array_equal(ids, pred.pop('case_ids')) or not np.array_equal(targets, pred.pop('targets')):
        raise ValueError('Frozen prediction alignment failure')
    known = set().union(*(rows[i][1] for i in np.flatnonzero(train_mask)))
    train_inv = {rows[i][2] for i in np.flatnonzero(train_mask)}
    dev_rows = [rows[i] for i in dev_idx]
    w = balanced_weights(ids).astype(float)
    w /= w.sum()

    def group(mask):
        cases = sorted(set(ids[mask].tolist()))
        mass = float(w[mask].sum())
        return dict(decisions=int(mask.sum()), paths=len(cases),
            game_seeds=len({records[i]['seed'] for i in cases}), original_weight_mass=mass,
            models={key: dict(
                conditional_mse=float(np.sum(w[mask] * (p[mask] - targets[mask]) ** 2) / mass) if mass else None,
                contribution_to_full_dev_mse=float(np.sum(w[mask] * (p[mask] - targets[mask]) ** 2)),
                share_of_full_dev_squared_error=float(np.sum(w[mask] * (p[mask] - targets[mask]) ** 2) / np.sum(w * (p - targets) ** 2)),
                mean_value=float(w[mask] @ p[mask] / mass) if mass else None,
                mean_return=float(w[mask] @ targets[mask] / mass) if mass else None)
            for key, p in pred.items()})

    report = dict(manifest=dict(experiment='E151', scope='read_only_post_hoc_coverage',
        code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        python=platform.python_version(), numpy=np.__version__),
        sources=dict(bank_sha256=file_hash(bank_path), evaluation_sha256=file_hash(eval_path),
                     tensors=bank['tensors'], predictions=ev['predictions'], original_runtime=bank['manifest']),
        alignment=dict(paths=len(records), raw_files_verified=2 * len(records), decisions=len(rows),
                       dev_decisions=len(ids), all_hashes_and_actions_pass=True),
        definitions=dict(identity='Base card/potion ID with unique TRAIN name aliases; relic name when ID absent. Upgrades not new base identities.',
            visible='Explicit player deck, hand, potions, relics; offered cards, potions, relics and bundle cards. Does not parse textual event references, powers, enemies or hidden state.',
            known='Identity appears anywhere in E148 TRAIN inputs; does not imply well learned or known in this role. Pre-E148 actor pretraining not audited.',
            inventory='Sorted owned deck multiset with exported upgrade flags, owned potions and relics. Excludes hand order, HP, energy, enemies, and future RNG.',
            weighting='Original full-DEV equal-path weights retained. Conditional MSE divides by group mass; additive contribution and error share use full DEV denominator.'),
        baseline_full_dev=group(np.ones(len(ids), dtype=bool)), coverage={}, groups={}, cases=[],
        new_game_actions=0, gradient_updates=0, new_model_inferences=0, final_acceptance_seeds_unused=True)
    masks = {}
    for scope, ix in (('owned', 0), ('visible', 1)):
        novel = [row[ix] - known for row in dev_rows]
        any_new = np.array([bool(x) for x in novel])
        masks[scope] = any_new
        ever = set(ids[any_new])
        report['groups'][scope] = {name: group(mask) for name, mask in (
            ('no_new_identity', ~any_new), ('new_identity', any_new),
            ('entire_path_no_new_identity', ~np.isin(ids, list(ever))),
            ('post_six_no_new_identity', (data['tasks'][dev_idx, 2] == 1) & ~any_new))}
        coverage = {}
        for kind in KINDS:
            train_vocab = {x for i in np.flatnonzero(train_mask) for x in rows[i][ix] if x[0] == kind}
            dev_vocab = {x for row in dev_rows for x in row[ix] if x[0] == kind}
            unknown = {x for x in dev_vocab - known if x[0] == kind}
            affected = np.array([any(x[0] == kind for x in ns) for ns in novel])
            coverage[kind] = dict(train_distinct_in_scope=len(train_vocab),
                train_distinct_any_visible=sum(x[0] == kind for x in known), dev_distinct_in_scope=len(dev_vocab),
                new_identities=sorted(x[1] for x in unknown), new_identity_count=len(unknown),
                affected_decisions=int(affected.sum()), affected_paths=len(set(ids[affected])),
                affected_game_seeds=len({records[i]['seed'] for i in ids[affected]}))
        report['coverage'][scope] = coverage
    new_inv = np.array([row[2] not in train_inv for row in dev_rows])
    report['groups']['inventory'] = {name: group(mask) for name, mask in (
        ('seen_inventory', ~new_inv), ('new_inventory', new_inv),
        ('known_visible_items_new_inventory', new_inv & ~masks['visible']))}
    report['inventory_counts'] = dict(train_unique=len(train_inv), dev_unique=len({r[2] for r in dev_rows}))
    for i in sorted(set(ids.tolist())):
        mask = ids == i
        report['cases'].append(dict(case=records[i]['case'], seed=records[i]['seed'], ascension=records[i]['ascension'],
            status=records[i]['status'], decisions=int(mask.sum()),
            owned_new_decisions=int((mask & masks['owned']).sum()), visible_new_decisions=int((mask & masks['visible']).sum()),
            new_inventory_decisions=int((mask & new_inv).sum())))
    g = report['groups']['visible']['no_new_identity']['models']
    report['decision_rule'] = dict(
        unseen_visible_identities_insufficient=all(
            g[key]['share_of_full_dev_squared_error'] > .5 and
            g[key]['conditional_mse'] > min(g['constant']['conditional_mse'], g['progress_ridge']['conditional_mse'])
            for key in ('2101-task', '2102-task')),
        inference='Descriptive sufficiency check, not a causal intervention or new policy evaluation. Familiar item combinations can still be novel.')
    report['seconds'] = time.monotonic() - start
    if report['seconds'] > 180:
        raise TimeoutError('Registered read-only budget')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('alignment', 'coverage', 'decision_rule', 'seconds')}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Preserve prior audit')
    main(a.output.resolve())
