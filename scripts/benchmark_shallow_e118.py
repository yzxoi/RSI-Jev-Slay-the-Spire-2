#!/usr/bin/env python3
"""Versioned short-horizon model calibration with per-configuration budgets."""
import argparse
import collections
import concurrent.futures
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from benchmark_minimal_e116 import write_json, sha_file, read_key, cluster_ci
from rsi.shallow_bench import (CONFIGS, INITIAL_CONFIGS, HORIZONS, make_bank, verify_bank, canonical,
    digest, request_body, reservation, parse_choice, truth)


class Ledger:
    def __init__(self, cap):
        self.cap, self.cost, self.unknown_reserved = cap, 0., 0.
        self.calls = self.invalid = self.consecutive_invalid = 0
        self.stop = None

    def acquire(self, reserve):
        if self.stop:
            return False
        if self.calls >= 104 or self.cost+self.unknown_reserved+reserve > self.cap:
            self.stop = 'call_or_spend_budget'
            return False
        self.calls += 1
        return True

    def settle(self, reserve, cost, valid):
        if not isinstance(cost, (float, int)) or not math.isfinite(cost) or cost < 0:
            self.unknown_reserved += reserve
            self.stop = 'unknown_billing'
        else:
            self.cost += cost
            if cost > reserve:
                self.stop = 'bill_exceeded_reservation'
        if valid:
            self.consecutive_invalid = 0
        else:
            self.invalid += 1
            self.consecutive_invalid += 1
        if self.consecutive_invalid >= 3 or (self.calls >= 20 and self.invalid/self.calls > .1):
            self.stop = self.stop or 'invalid_response_exit'

    def as_dict(self):
        return vars(self).copy()


def http_worker():
    args = json.load(sys.stdin)
    if args['endpoint'] not in ('https://openrouter.ai/api/v1/systemone',
                                'https://openrouter.ai/api/v1/chat/completions'):
        raise ValueError('Unexpected endpoint')
    try:
        req = urllib.request.Request(args['endpoint'], data=canonical(args['body']).encode(),
            headers={'Authorization': 'Bearer '+args['key'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as res:
            reply = {'response': json.load(res)}
    except urllib.error.HTTPError as exc:
        reply = {'error': f'http_{exc.code}', 'error_body': exc.read().decode(errors='replace')[:12000]}
    except Exception as exc:
        reply = {'error': type(exc).__name__ + ': ' + str(exc)}
    print(canonical(reply).replace(args['key'], '[redacted]'))


def post(config, body, key):
    endpoint = 'https://openrouter.ai/api/v1/' + ('systemone' if config == 'jev' else 'chat/completions')
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), '_worker'],
            input=canonical(dict(endpoint=endpoint, body=body, key=key)),
            text=True, capture_output=True, timeout=60, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {'error': 'total_http_deadline_60s'}
    if p.returncode:
        return {'error': 'worker_failed'}
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {'error': 'non_json_worker_response'}


def reasoning_tokens(usage):
    if 'reasoning_tokens' in usage:
        return usage['reasoning_tokens']
    return (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')


def score(config, item, task, reply):
    result = reply.get('response') or {}
    error, choice = reply.get('error'), None
    if not error:
        try:
            choice = parse_choice(config, result)
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            error = str(exc)
    usage = result.get('usage') or {}
    row = dict(config=config, item_id=item['id'], seed=item['seed'], horizon=item['horizon'], task=task,
        expected=truth(item, task), choice=choice, valid=error is None, error=error,
        correct=error is None and choice == truth(item, task),
        resolved_model=result.get('model'), provider=result.get('provider'), usage=usage,
        reasoning_tokens=reasoning_tokens(usage))
    if task in ('choice', 'readout'):
        row['root_q'] = item['root_q']
        row['root_regret'] = max(item['root_q'].values())-item['root_q'][choice] if row['valid'] else None
    else:
        row['semantic_truth'] = item['route_truth']
        row['semantic_yes'] = (choice == ('A' if task == 'predict_yes_a' else 'B')) if row['valid'] else None
    if config == 'jev':
        row['probabilities'] = result.get('answers', {}).get('answer', {}).get('probabilities')
    return row


def run_config(config, bank, key, out):
    folder = out/config; folder.mkdir()
    items = {x['id']: x for x in bank['items']}
    ledger = Ledger(CONFIGS[config]['cap'])
    rows, started = [], time.monotonic()
    with (folder/'trace.jsonl').open('x') as trace:
        for index, cell in enumerate(bank['schedule']):
            item, task = items[cell['item_id']], cell['task']
            body = request_body(config, item, task)
            reserve = reservation(config, body)
            if time.monotonic()-started >= 1500:
                ledger.stop = ledger.stop or 'batch_deadline'
            if not ledger.acquire(reserve):
                row = score(config, item, task, {'error': 'unstarted: '+ledger.stop})
                row['attempted'] = False
                rows.append(row)
                continue
            trace.write(canonical(dict(kind='request', index=index, cell=cell, body=body, reservation=reserve))+'\n')
            trace.flush(); os.fsync(trace.fileno())
            start = time.monotonic()
            reply = post(config, body, key)
            elapsed = time.monotonic()-start
            trace.write(canonical(dict(kind='response', index=index, cell=cell, seconds=elapsed, reply=reply))+'\n')
            trace.flush(); os.fsync(trace.fileno())
            row = score(config, item, task, reply)
            row.update(attempted=True, seconds=elapsed, request_sha256=digest(body), response_sha256=digest(reply))
            rows.append(row)
            ledger.settle(reserve, row['usage'].get('cost'), row['valid'])
            if ledger.calls % 8 == 0 or ledger.stop:
                print(canonical(dict(config=config, completed=ledger.calls, planned=104,
                    cost_usd=ledger.cost, invalid=ledger.invalid, stop=ledger.stop,
                    elapsed=round(time.monotonic()-started, 1))), flush=True)
    manifest = dict(config=config, ledger=ledger.as_dict(), elapsed_seconds=time.monotonic()-started,
                    trace_sha256=sha_file(folder/'trace.jsonl'))
    write_json(folder/'rows.json', rows)
    write_json(folder/'manifest.json', manifest)
    return manifest


def accuracy(rows):
    return dict(n=len(rows), attempted=sum(r.get('attempted', False) for r in rows),
        valid=sum(r['valid'] for r in rows), correct=sum(r['correct'] for r in rows),
        accuracy=statistics.mean(r['correct'] for r in rows),
        bootstrap_seed_95=cluster_ci(rows, lambda r: int(r['correct'])))


def summarize(bank, out):
    configs = json.loads((out/'manifest.json').read_text())['configurations']
    results = {}
    all_rows = {}
    for config in configs:
        rows = json.loads((out/config/'rows.json').read_text()); all_rows[config] = rows
        lookup = {(r['item_id'], r['task']): r for r in rows}
        pairs = []
        for item in bank['items']:
            a, b = (lookup[item['id'], t] for t in ('predict_yes_a', 'predict_yes_b'))
            pairs.append(dict(seed=item['seed'], horizon=item['horizon'], item_id=item['id'],
                both_correct=a['correct'] and b['correct'],
                semantic_consistent=a['valid'] and b['valid'] and a['semantic_yes'] == b['semantic_yes']))
        by_horizon = {}
        readout = accuracy([r for r in rows if r['task'] == 'readout'])
        reliable = sum(r['valid'] for r in rows)/len(rows) >= .95 and readout['correct'] >= 7
        prefix = 0; prefix_open = True
        for h in HORIZONS:
            group = [p for p in pairs if p['horizon'] == h]
            stats = {t: accuracy([r for r in rows if r['task'] == t and r['horizon'] == h])
                     for t in ('choice', 'predict_yes_a', 'predict_yes_b')}
            paired_correct = sum(p['both_correct'] for p in group)
            passed = reliable and stats['choice']['correct'] >= 7 and paired_correct >= 7
            stats.update(prediction_both_mappings_correct=paired_correct, prediction_pairs=len(group),
                         semantic_consistent=sum(p['semantic_consistent'] for p in group), exploratory_gate_passed=passed)
            by_horizon[str(h)] = stats
            if prefix_open and passed:
                prefix = h
            else:
                prefix_open = False
        latency = sorted(r['seconds'] for r in rows if r.get('attempted'))
        rt = [r['reasoning_tokens'] for r in rows if r.get('attempted') and r['reasoning_tokens'] is not None]
        usage = [r['usage'] for r in rows if r.get('attempted')]
        results[config] = dict(
            configuration=CONFIGS[config], readout=readout, by_horizon=by_horizon,
            overall={t: accuracy([r for r in rows if r['task'] == t]) for t in ('choice', 'predict_yes_a', 'predict_yes_b')},
            prediction_both_correct=sum(p['both_correct'] for p in pairs), prediction_worlds=32,
            semantic_consistent=sum(p['semantic_consistent'] for p in pairs),
            yes_answers={t: sum(r.get('semantic_yes') is True for r in rows if r['task']==t)
                         for t in ('predict_yes_a','predict_yes_b')},
            label_A_answers={t: sum(r['choice']=='A' for r in rows if r['task']==t)
                         for t in ('predict_yes_a','predict_yes_b')},
            reliable=reliable, empirical_contiguous_passing_prefix=prefix,
            range_right_censored=prefix==max(HORIZONS),
            reasoning_counter_present=len(rt), reasoning_tokens_reported=sum(rt),
            all_reported_reasoning_counters_zero=bool(rt) and all(n==0 for n in rt),
            usage_totals=dict(input_tokens=sum(u.get('input_tokens',u.get('prompt_tokens',0)) for u in usage),
                output_tokens=sum(u.get('output_tokens',u.get('completion_tokens',0)) for u in usage),
                cost=sum(u.get('cost',0) or 0 for u in usage)),
            models=dict(collections.Counter(r.get('resolved_model') or '[missing]' for r in rows if r.get('attempted'))),
            providers=dict(collections.Counter(r.get('provider') or '[missing]' for r in rows if r.get('attempted'))),
            latency=dict(p50=statistics.median(latency) if latency else None,
                p95=latency[math.ceil(.95*len(latency))-1] if latency else None),
            manifest=json.loads((out/config/'manifest.json').read_text()))
    base = {(r['item_id'],r['task']):r for r in all_rows['jev']}
    contrasts = {}
    for config in configs:
        if config == 'jev': continue
        diffs = [dict(seed=r['seed'],delta=int(r['correct'])-int(base[r['item_id'],r['task']]['correct']))
                 for r in all_rows[config] if r['task']=='choice' and r['horizon'] in (4,8)]
        gain = statistics.mean(d['delta'] for d in diffs)
        passes = any(results[config]['by_horizon'][str(h)]['exploratory_gate_passed'] and
                     not results['jev']['by_horizon'][str(h)]['exploratory_gate_passed'] for h in (4,8))
        contrasts[config] = dict(n=16, root_accuracy_gain_h4_h8=gain,
            bootstrap_seed_95=cluster_ci(diffs,lambda d:d['delta']),
            promising_configuration_contrast=results[config]['reliable'] and results['jev']['reliable'] and passes and gain>=.20)
    return dict(configurations=results, contrasts_vs_jev=contrasts,
        verification=verify_bank(bank), total_reported_cost_usd=sum(x['usage_totals']['cost'] for x in results.values()),
        total_unknown_reservation_usd=sum(x['manifest']['ledger']['unknown_reserved'] for x in results.values()),
        planned_calls=104*len(configs), attempted_calls=sum(r.get('attempted',False) for rs in all_rows.values() for r in rs),
        valid_calls=sum(r['valid'] for rs in all_rows.values() for r in rs),
        limitations=['Exploratory eight seed clusters; paired mappings are not independent worlds.',
            'Model configurations differ in interface, reasoning and actual compute; not a compute-matched ranking.',
            'Prompt length covaries with horizon; disjoint root components allow connectivity shortcuts.',
            'A passing prefix is an empirical task result, not an internal architectural depth.',
            'Bootstrap intervals collapse at perfect/zero observed performance; no guarantee on unseen tasks.'])


def audit(bank, out):
    top = json.loads((out/'manifest.json').read_text())
    assert digest(bank) == top['bank_digest']
    assert canonical(make_bank()) == canonical(bank)
    verify_bank(bank)
    lookup = {i['id']:i for i in bank['items']}
    counts = {}
    for config, snapshot in top['configurations'].items():
        assert snapshot == CONFIGS[config], 'Configuration changed since the run'
        folder = out/config
        rows = json.loads((folder/'rows.json').read_text())
        manifest = json.loads((folder/'manifest.json').read_text())
        events = [json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
        assert manifest['trace_sha256'] == sha_file(folder/'trace.jsonl')
        assert len(rows)==104 and len({(r['item_id'],r['task']) for r in rows})==104
        for row,cell in zip(rows,bank['schedule']):
            assert (row['item_id'],row['task'])==(cell['item_id'],cell['task'])
        ledger = Ledger(CONFIGS[config]['cap'])
        for n in range(0,len(events),2):
            req,res=events[n:n+2]
            idx=req['index']; cell=bank['schedule'][idx]
            assert req['kind']=='request' and res['kind']=='response'
            assert req['index']==res['index'] and req['cell']==res['cell']==cell
            item=lookup[cell['item_id']]; body=request_body(config,item,cell['task'])
            assert req['body']==body and rows[idx]['request_sha256']==digest(body)
            assert rows[idx]['response_sha256']==digest(res['reply'])
            assert all(rows[idx][k]==v for k,v in score(config,item,cell['task'],res['reply']).items())
            reserve=reservation(config,body)
            assert reserve==req['reservation'] and ledger.acquire(reserve)
            ledger.settle(reserve,rows[idx]['usage'].get('cost'),rows[idx]['valid'])
        assert len(events)//2==sum(r.get('attempted',False) for r in rows)==ledger.calls
        assert abs(ledger.cost-manifest['ledger']['cost'])<1e-9
        assert abs(ledger.unknown_reserved-manifest['ledger']['unknown_reserved'])<1e-9
        assert ledger.cost+ledger.unknown_reserved <= CONFIGS[config]['cap']+1e-9
        counts[config]=ledger.calls
    recomputed=summarize(bank,out)
    assert recomputed==json.loads((out/'summary.json').read_text())
    result=dict(passed=True,request_response_pairs=counts,fixtures_regenerated=True,
                total_cost=recomputed['total_reported_cost_usd'],unknown_reservation=recomputed['total_unknown_reservation_usd'])
    write_json(out/'audit.json',result)
    return result


def continuation_plan(source, bank, selected):
    """Check previous spend and prohibit repeated inference before reading a key."""
    if len(set(selected)) != len(selected) or not selected or any(c not in CONFIGS for c in selected):
        raise ValueError('Unknown, duplicate or empty configuration selection')
    prior = json.loads((source/'manifest.json').read_text()) if source else None
    reused = prior['configurations'] if prior else {}
    if set(selected) & set(reused):
        raise ValueError('A continuation must not repeat any previous configuration')
    if 'jev' not in set(selected) | set(reused):
        raise ValueError('A measured Jev baseline is required')
    spent = 0.
    if prior:
        assert prior['bank_digest'] == digest(bank)
        audit(bank, source)
        summary = json.loads((source/'summary.json').read_text())
        spent = summary['total_reported_cost_usd'] + summary['total_unknown_reservation_usd']
    ceiling = spent + sum(CONFIGS[c]['cap'] for c in selected)
    if ceiling > 3 + 1e-9:
        raise ValueError('Combined conservative budget exceeds $3')
    return prior, dict(reused), spent, ceiling


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('command',choices=('freeze','run','audit','_worker'))
    p.add_argument('--bank',default='experiments/E118/fixtures.json')
    p.add_argument('--output',default='artifacts/runs/e118-pilot-v1')
    p.add_argument('--env-file',default=str(ROOT/'.env'))
    p.add_argument('--execute',action='store_true')
    p.add_argument('--configs', nargs='+', choices=tuple(CONFIGS), default=list(INITIAL_CONFIGS))
    p.add_argument('--continue-from', type=Path)
    args=p.parse_args()
    if args.command=='_worker': return http_worker()
    if args.command=='freeze':
        if Path(args.bank).exists(): raise SystemExit('Frozen bank already exists')
        bank=make_bank(); verified=verify_bank(bank)
        Path(args.bank).write_text(canonical(bank)+'\n')
        print(canonical(dict(**verified,sha256=sha_file(args.bank)))); return
    bank=json.loads(Path(args.bank).read_text()); verify_bank(bank)
    out=Path(args.output)
    if args.command=='audit':
        assert sha_file(args.bank)==json.loads((out/'manifest.json').read_text())['fixture_sha256']
        print(json.dumps(audit(bank,out),indent=2)); return
    if not args.execute: raise SystemExit('--execute required for paid requests')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise SystemExit('Tracked work must be committed before paid evaluation')
    subprocess.check_call(['git','ls-files','--error-unmatch',str(Path(args.bank).resolve().relative_to(ROOT))],cwd=ROOT,stdout=subprocess.DEVNULL)
    prior, reused, spent, ceiling = continuation_plan(args.continue_from, bank, args.configs)
    configs = {**reused, **{c:CONFIGS[c] for c in args.configs}}
    key=read_key(args.env_file)
    out.mkdir(parents=True,exist_ok=False)
    for c in reused:
        shutil.copytree(args.continue_from/c, out/c)
    manifest=dict(experiment='E118',tested_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version,platform=platform.platform(),bank_digest=digest(bank),fixture_sha256=sha_file(args.bank),
        metadata_sha256=sha_file(ROOT/'experiments/E118/model-metadata.json'),configurations=configs,
        total_budget_usd=3,planned_calls=104*len(configs),workers=len(args.configs),http_deadline_seconds=60,configuration_deadline_seconds=1500,
        start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),automatic_retries=0)
    manifest.update(active_configurations=args.configs, new_planned_calls=104*len(args.configs),
        reused_configurations=list(reused), previous_cost_plus_reservations=spent, combined_conservative_ceiling=ceiling,
        config_tested_shas={c:(prior.get('config_tested_shas',{}).get(c,prior['tested_sha']) if c in reused else manifest['tested_sha']) for c in configs})
    if prior:
        manifest['continuation_source'] = dict(path=str(args.continue_from),
            manifest_sha256=sha_file(args.continue_from/'manifest.json'),
            summary_sha256=sha_file(args.continue_from/'summary.json'))
        manifest['replacement_metadata_sha256'] = sha_file(ROOT/'experiments/E118/replacement-model-metadata.json')
    write_json(out/'manifest.json',manifest)
    started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.configs)) as pool:
        futures=[pool.submit(run_config,c,bank,key,out) for c in args.configs]
        for f in concurrent.futures.as_completed(futures):
            print(canonical({'configuration_done':f.result()}),flush=True)
    manifest.update(elapsed_seconds=time.monotonic()-started,
        completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    write_json(out/'manifest.json',manifest)
    summary=summarize(bank,out); write_json(out/'summary.json',summary)
    print(canonical({'done':str(out),'cost':summary['total_reported_cost_usd'],'valid':summary['valid_calls']}))


if __name__=='__main__': main()
