#!/usr/bin/env python3
"""Prospective natural opening collection and separately timed bounded search."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import statistics
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.battle_search import finish
from rsi.bounded_opening import bounded_choices
from rsi.campaign_teacher import Ownership
from rsi.checkpoints import wire_pairs
from rsi.continuation import FrozenProgram
from rsi.engine import Headless
from rsi.opening_subset import candidate_id, indexes, opening_domain, pick, rank
from rsi.resources import require_resource_interface
from rsi.run_env import legal_choices, replay, run_outcome
from rsi.trace import Trace, digest
from scripts.evaluate_battle_search_e120 import audit, write
from scripts.pilot_root_teacher_e149 import checked, info, same_runtime, version
from scripts.search_opening_e169 import trial

POLICIES = ['rsi/bounded_opening.py', 'rsi/opening_subset.py', 'rsi/continuation.py',
            'rsi/teacher.py', 'rsi/planner.py', 'rsi/ppo_actions.py', 'rsi/potions.py',
            'rsi/curriculum.py', 'scripts/search_opening_e169.py', 'scripts/compare_opening_e171.py']


def plan(v):
    return dict(manifest=v, collection=[dict(case=f'A{a}-{i:03}',
        seed=f'e171_opening_Ironclad_A{a}_{i:03}', character='Ironclad', ascension=a, index=i)
        for i in range(32) for a in (0, 5)], policy_sources=[info(ROOT / f) for f in POLICIES],
        budgets=dict(collection=300, evaluation=900, seed_seconds=120, seed_actions=2400,
                     trial_seconds=120, trial_actions=300, workers=4),
        protocol=info(ROOT / 'experiments/E171/README.md'),
        scope='Mechanism-conditioned new seeds. No replacement, no full-run or native claim.')


def check_plan(path, v):
    p = checked(path, tracked=True)
    same_runtime(p, v)
    for s in p['policy_sources']:
        if info(ROOT / s['path']) != s:
            raise ValueError('Changed frozen policy: ' + s['path'])
    return p


def collect_one(config, v, deadline):
    trace = Trace(ROOT / 'artifacts/runs' / str(uuid.uuid4()),
                  dict(**v, scope='E171_natural_opening_collection', config=config))
    started = time.monotonic()
    r = dict(**config, status='error', steps=0, illegal_actions=0, map_queries=0)
    engine = None
    state = {}; prior = {}; previous = None; history = {}; transitions = []
    owner = Ownership(); program = FrozenProgram(None); last = None; repeated = 0

    def send(command):
        left = min(120 - (time.monotonic() - started), deadline - time.monotonic())
        if left <= 0:
            raise TimeoutError('Collection per-seed/global cap')
        engine.timeout = min(15, left)
        return engine.send(command)

    try:
        if time.monotonic() >= deadline:
            raise TimeoutError('Not started before collection cap')
        engine = Headless(trace.directory, timeout=15, resource_decisions=True)
        state = send(dict(cmd='start_run', **{k: config[k] for k in ('seed', 'character', 'ascension')}))
        require_resource_interface(state)
        for step in range(2401):
            terminal = run_outcome(state)
            if terminal:
                r['status'] = terminal
                break
            # Stop BEFORE executing a potentially ambiguous opening menu.
            c = state.get('context') or {}
            entered = (state['decision'] == 'card_select' and previous is not None
                       and previous['action'].get('action') == 'select_map_node'
                       and c.get('room_type') in ('Monster', 'Elite', 'Boss'))
            if entered:
                try:
                    domain = opening_domain(state, previous['action'], prior)
                except ValueError as exc:
                    r.update(status='unsupported', reason=str(exc))
                    break
                choices = legal_choices(state, history)
                baseline = program.choose(state, choices, previous)[0]
                r.update(status='opening_candidate', candidate=dict(
                    state=state, previous_state=prior, previous=previous, domain=domain,
                    entry_command=previous['action'], choices=choices, baseline=baseline,
                    prefix_count=1 + r['steps'] + r['map_queries']))
                break
            active, _ = owner.observe(state)
            if state['decision'] == 'map_select' and c.get('room_type') == 'Map':
                send(dict(cmd='get_map'))  # A read; preserve the actual decision state.
                r['map_queries'] += 1
            if step == 2400:
                r['status'] = 'action_cap'
                break
            before = digest(state)
            repeated = repeated + 1 if before == last else 0
            last = before
            if repeated >= 5:
                raise ValueError('Six repeated states')
            choices = legal_choices(state, history)
            if len(choices) == 1:
                chosen, meta = choices[0], dict(route='only_legal')
            else:
                chosen, meta = program.choose(state, choices, previous)
            if chosen['action'] not in [c['action'] for c in choices]:
                r['illegal_actions'] += 1
                raise ValueError('Illegal current action')
            trace.write('decision', dict(state=state, before=before, candidates=choices,
                                        chosen=chosen, combat_active=active, **meta))
            program.remember(state, chosen)
            if state['decision'] == 'map_select':
                history['removed_here'] = False
            if chosen['action']['action'] == 'remove_card':
                history['removed_here'] = True
            prior = state
            state = send(chosen['action'])
            r['steps'] += 1
            transitions.append(dict(before=before, action=chosen['action'], after=digest(state)))
            previous = chosen
    except TimeoutError as exc:
        r.update(status='timeout', error=str(exc))
    except Exception as exc:
        r.update(status='error', error=f'{type(exc).__name__}: {exc}')
    r.update(final_context=state.get('context'), final_hp=state.get('player', {}).get('hp'),
             final_hash=digest(state), transition_hash=digest(transitions))
    finish(trace, r, engine, started)
    return r


def collect(v, p, output, plan_path):
    started = time.monotonic(); deadline = started + p['budgets']['collection']
    directory = output.with_suffix(''); directory.mkdir(parents=True, exist_ok=False)

    def one(config):
        r = collect_one(config, v, deadline)
        write(directory / (r['case'] + '.json'), r)
        print(json.dumps(dict(case=r['case'], status=r['status'], context=r['final_context'])), flush=True)
        return r

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, p['collection']))
    seconds = time.monotonic() - started
    return dict(manifest=v, plan=info(plan_path), records=records, seconds=seconds,
                statuses=dict(Counter(r['status'] for r in records)), raw_audit=audit(records),
                within_budget=seconds <= 300, model_api_calls=0)


def bank(v, p, plan_path, collection_path, review_path):
    collection = checked(collection_path, tracked=True); review = checked(review_path, tracked=True)
    same_runtime(collection, v)
    if collection['plan'] != info(plan_path) or review['collection'] != info(collection_path):
        raise ValueError('Mismatched collection or origin review')
    if [r['seed'] for r in collection['records']] != [c['seed'] for c in p['collection']]:
        raise ValueError('Changed collection cohort/order')
    if not audit(collection)['pass']:
        raise ValueError('Changed raw collection')
    candidates = [r for r in collection['records'] if r['status'] == 'opening_candidate']
    if {r['case'] for r in review['roots']} != {r['case'] for r in candidates}:
        raise ValueError('Origin review must include every candidate')
    for source in review['source_evidence']:
        if info(ROOT / source['path']) != source:
            raise ValueError('Changed independent source evidence')
    counts = Counter(); roots = []
    for record in candidates:
        reviewed = next(r for r in review['roots'] if r['case'] == record['case'])
        if not reviewed['eligible'] or counts[record['ascension']] == 3:
            continue
        c = record['candidate']; state = c['state']
        if reviewed['state_hash'] != digest(state) or not reviewed['reason']:
            raise ValueError('Stale or unreasoned origin review')
        wire = Path(record['trace_path']).with_name('wire.jsonl')
        pairs = wire_pairs(ROOT / wire)
        if len(pairs) != c['prefix_count'] or digest(pairs[-1][1]) != digest(state):
            raise ValueError('Not an exact unfinished opening prefix')
        domain = opening_domain(state, pairs[-1][0], c['previous_state'])
        domain['evidence'] = reviewed['reason']
        small = bounded_choices(state, c['choices'], c['baseline'], domain)
        counts[record['ascension']] += 1
        roots.append(dict(case=record['case'], seed=record['seed'], ascension=record['ascension'],
            wire=info(ROOT / wire), prefix_count=len(pairs), entry_hash=digest(state), domain=domain,
            previous=c['previous'], choices=c['choices'], bounded_choices=small,
            baseline_id=candidate_id(c['baseline']), source_record={k: val for k, val in record.items() if k != 'candidate'},
            origin_review=reviewed, context=state['context'], entry_hp=state['player']['hp'],
            cards=[{k: card.get(k) for k in ('index', 'name', 'id', 'type', 'cost', 'upgraded')} for card in state['cards']],
            scope='E171_unseen_opening_counterfactual'))
    return dict(manifest=v, plan=info(plan_path), collection=info(collection_path), review=info(review_path),
                roots=roots, per_difficulty=dict(counts), coverage_pass=len(roots) == 6)


def compact(r):
    return {k: r.get(k) for k in ('candidate_id', 'discard_indices', 'status', 'hp', 'potions', 'steps')}


def evaluate(v, p, plan_path, bank_path, output):
    b = checked(bank_path, tracked=True); same_runtime(b, v)
    if b['plan'] != info(plan_path):
        raise ValueError('Changed root plan')
    started = time.monotonic(); deadline = started + 900
    directory = output.with_suffix(''); directory.mkdir(parents=True, exist_ok=False)
    results = []; proofs = []; fresh = []; decisions = []

    def run(root, choice, tag):
        r = trial(root, choice, v, deadline, tag)
        write(directory / (r['case'] + '.json'), r)
        return r

    def verify(record, role):
        r = replay(record, v, seconds=max(.001, min(120, deadline - time.monotonic())))
        return dict(root=record['root'], role=role, record=r,
                    matches=r['status'] == 'match' and r.get('final_hash') == record.get('final_hash'))

    for i, root in enumerate(b['roots']):
        baseline = run(root, next(c for c in root['choices'] if candidate_id(c) == root['baseline_id']), 'baseline')
        row = dict(case=root['case'], seed=root['seed'], ascension=root['ascension'], baseline=baseline, arms={})
        row['arm_order'] = ['8', '32'] if i % 2 == 0 else ['32', '8']
        for arm in row['arm_order']:
            clock = time.monotonic()
            choices = root['bounded_choices'] if arm == '8' else root['choices']
            with ThreadPoolExecutor(max_workers=4) as pool:
                records = list(pool.map(lambda c: run(root, c, 'arm' + arm), choices))
            complete = all(r['status'] in ('clear', 'defeat') and not r.get('error') for r in records)
            best = pick(records) if complete else None
            decision = dict(root=root['case'], arm=arm, candidate_id=best['candidate_id'] if best else None)
            write(directory / f"{root['case']}-arm{arm}-frozen-choice.json", decision)
            elapsed = time.monotonic() - clock
            decisions.append(decision)
            row['arms'][arm] = dict(records=records, selected=best, complete=complete,
                                    candidates=len(choices), seconds=elapsed)
            print(json.dumps(dict(case=root['case'], arm=arm, seconds=elapsed,
                                  baseline=compact(baseline), selected=compact(best) if best else None)), flush=True)
        # Save outcomes before any fresh-execution evidence is available.
        results.append(row); write(directory / (root['case'] + '-result.json'), row)
        selected = [(baseline, 'baseline')] + [(a['selected'], arm) for arm, a in row['arms'].items() if a['selected']]
        with ThreadPoolExecutor(max_workers=4) as pool:
            proofs.extend(pool.map(lambda x: verify(*x), selected))
        for arm, a in row['arms'].items():
            if a['selected']:
                choice = next(c for c in root['choices'] if candidate_id(c) == a['selected']['candidate_id'])
                r = run(root, choice, 'fresh' + arm)
                fresh.append(dict(root=root['case'], arm=arm, record=r,
                    matches=all(r.get(k) == a['selected'].get(k) for k in ('status', 'final_hash', 'transition_hash'))
                    and not r.get('error')))
    summaries = []
    for row in results:
        if row['baseline']['status'] not in ('clear', 'defeat') or row['baseline'].get('error') or not all(a['complete'] for a in row['arms'].values()):
            summaries.append(dict(case=row['case'], complete=False)); continue
        base = row['baseline']; small = row['arms']['8']['selected']; full = row['arms']['32']['selected']
        hp = lambda r: r['hp'] if r['status'] == 'clear' else 0
        shared = {r['candidate_id']: r for r in row['arms']['32']['records']}
        shared_match = all(all(r.get(k) == shared[r['candidate_id']].get(k) for k in ('status', 'final_hash', 'transition_hash'))
                           for r in row['arms']['8']['records'])
        base_match = all(all(next(r for r in a['records'] if r['candidate_id'] == base['candidate_id']).get(k) == base.get(k)
                            for k in ('status', 'final_hash', 'transition_hash')) for a in row['arms'].values())
        summaries.append(dict(case=row['case'], seed=row['seed'], ascension=row['ascension'], complete=True,
            baseline=compact(base), bounded=compact(small), exhaustive=compact(full),
            improved=rank(small) > rank(base), full_improved=rank(full) > rank(base),
            no_lost_clear=base['status'] != 'clear' or (small['status'] == full['status'] == 'clear'),
            retained_full_clear=full['status'] != 'clear' or small['status'] == 'clear',
            small_hp_gain=max(0, hp(small) - hp(base)), full_hp_gain=max(0, hp(full) - hp(base)),
            shared_match=shared_match, baseline_match=base_match,
            seconds={arm: a['seconds'] for arm, a in row['arms'].items()},
            clears={arm: sum(r['status'] == 'clear' for r in a['records']) for arm, a in row['arms'].items()}))
    raw = audit([results, proofs, fresh]); seconds = time.monotonic() - started
    integrity = (bool(results) and len(proofs) == 3 * len(results) and len(fresh) == 2 * len(results)
        and all(s['complete'] and s['shared_match'] and s['baseline_match'] for s in summaries)
        and all(r['matches'] for r in proofs + fresh) and raw['pass'] and seconds <= 900)
    valid = [s for s in summaries if s['complete']]
    full_gain = sum(s['full_hp_gain'] for s in valid)
    retention = sum(s['small_hp_gain'] for s in valid) / full_gain if full_gain else None
    latencies = {}
    for arm in ('8', '32'):
        xs = sorted(r['arms'][arm]['seconds'] for r in results)
        latencies[arm] = dict(n=len(xs), median=statistics.median(xs) if xs else None,
                             p95=xs[math.ceil(.95 * len(xs)) - 1] if xs else None)
    gates = dict(coverage=b['coverage_pass'], fidelity=integrity,
        no_lost_baseline_clear=bool(valid) and all(s['no_lost_clear'] for s in valid),
        improved_two_seeds=len({s['seed'] for s in valid if s['improved']}) >= 2,
        retains_full_clears=bool(valid) and all(s['retained_full_clear'] for s in valid),
        retains_90_percent_hp=retention is not None and retention >= .9,
        latency=bool(results) and latencies['8']['median'] <= 30 and latencies['8']['p95'] <= 60)
    return dict(manifest=v, plan=info(plan_path), bank=info(bank_path), results=results, proofs=proofs,
        fresh=fresh, decisions=decisions, summaries=summaries, raw_audit=raw, seconds=seconds,
        integrity_pass=integrity, hp_gain_retention=retention, latencies=latencies, gates=gates,
        deployment_gate=all(gates.values()), default_promotion=False, model_api_calls=0, full_runs_evaluated=0)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['plan', 'collect', 'bank', 'evaluate'])
    for name in ('plan', 'collection', 'review', 'bank', 'output'):
        ap.add_argument('--' + name, type=Path, required=name == 'output')
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('Never overwrite evidence')
    v = {**version(), 'experiment': 'E171'}
    p = check_plan(a.plan, v) if a.mode != 'plan' else None
    if a.mode == 'plan': value = plan(v)
    elif a.mode == 'collect': value = collect(v, p, a.output, a.plan)
    elif a.mode == 'bank': value = bank(v, p, a.plan, a.collection, a.review)
    else: value = evaluate(v, p, a.plan, a.bank, a.output)
    write(a.output, value)
    print(json.dumps({k: val for k, val in value.items() if k in
        ('statuses', 'seconds', 'per_difficulty', 'coverage_pass', 'integrity_pass', 'gates', 'deployment_gate', 'latencies', 'hp_gain_retention')}))
