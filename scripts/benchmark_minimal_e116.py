#!/usr/bin/env python3
"""Freeze, evaluate and summarize E116. Paid execution requires --execute."""
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.minimal_decision import (ARMS, ENDPOINT, HORIZONS, MODEL, SEEDS,
                                answer_key, canonical, digest, make_bank,
                                request, verify_bank)


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_key(path):
    key = os.environ.get('OPENROUTER_RSI_JEV_KEY')
    if key:
        return key
    for line in Path(path).read_text().splitlines():
        if line.strip().startswith('OPENROUTER_RSI_JEV_KEY='):
            return line.split('=', 1)[1].strip().strip('\"\'')
    raise RuntimeError('Missing OPENROUTER_RSI_JEV_KEY')


def worker():
    args = json.load(sys.stdin)
    try:
        req = urllib.request.Request(ENDPOINT, data=canonical(args['body']).encode(),
            headers={'Authorization': 'Bearer ' + args['key'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=25) as response:
            result = {'response': json.load(response)}
    except Exception as exc:
        # Error text can contain server data; the full key is always redacted.
        result = {'error': (type(exc).__name__ + ': ' + str(exc)).replace(args['key'], '[redacted]')}
    print(canonical(result))


def post(body, key):
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), '_worker'],
            input=canonical({'body': body, 'key': key}), capture_output=True,
            text=True, timeout=25, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {'error': 'total_http_deadline_25s'}
    if p.returncode:
        return {'error': 'http_worker_failed'}
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {'error': 'non_json_worker_response'}


def validate_response(result):
    model = result.get('model', '')
    if not (model == MODEL or model.startswith(MODEL + '-')):
        return 'unexpected_model'
    if result.get('provider') != 'TypeSafe':
        return 'unexpected_provider'
    choice = result.get('answers', {}).get('answer', {}).get('choice')
    if choice not in ('A', 'B'):
        return 'invalid_choice'
    return None


def score(item, arm, result, error=None):
    ans = result.get('answers', {}).get('answer', {})
    error = error or validate_response(result)
    chosen = ans.get('choice')
    truth = answer_key(item, arm)
    row = {'item_id': item['id'], 'seed': item['seed'], 'horizon': item['horizon'],
           'arm': arm, 'answer': truth, 'choice': chosen, 'valid': error is None,
           'correct': error is None and chosen == truth, 'error': error,
           'confidence': ans.get('confidence'), 'probabilities': ans.get('probabilities'),
           'resolved_model': result.get('model'), 'provider': result.get('provider'),
           'usage': result.get('usage', {})}
    if arm != 'prediction':
        q = item['certificate'].get(arm + '_q', item['certificate']['root_q'])
        row['root_q'] = q
        # Operational failure gets no action-value assignment; accuracy includes it.
        row['root_regret'] = max(q.values()) - q[chosen] if row['valid'] else None
    probabilities = ans.get('probabilities', {})
    if (isinstance(probabilities, dict) and set(probabilities) == {'A', 'B'} and
        all(isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1
            for p in probabilities.values()) and abs(sum(probabilities.values()) - 1) < .01):
        row['binary_brier'] = (probabilities['A'] - int(truth == 'A')) ** 2
    return row


def run(args):
    if not args.execute:
        raise SystemExit('Use --execute for the fixed paid experiment.')
    bank_path = Path(args.bank)
    bank = json.loads(bank_path.read_text())
    verify_bank(bank)
    # The fixture file and executable must already be committed, never silently tuned.
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True).strip():
        raise SystemExit('Refusing paid evaluation with tracked working-tree changes.')
    subprocess.check_call(['git', 'ls-files', '--error-unmatch', str(bank_path.resolve().relative_to(ROOT))],
                          cwd=ROOT, stdout=subprocess.DEVNULL)
    key = read_key(args.env_file)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'experiment': 'E116', 'tested_sha': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'fixture_sha256': sha_file(bank_path), 'bank_digest': digest(bank),
        'command': [sys.executable, str(Path(__file__).relative_to(ROOT)), 'run',
                    '--bank', str(bank_path), '--output', str(out), '--env-file', '<local ignored .env>', '--execute'],
        'model_requested': MODEL, 'endpoint': ENDPOINT, 'python': sys.version,
        'platform': platform.platform(), 'start_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'planned_requests': 216, 'max_cost_usd': .20, 'per_call_reservation_usd': .005,
        'max_batch_seconds': 1200, 'http_total_deadline_seconds': 25,
        'provider_fallback': False, 'automatic_retries': 0,
        'hidden_reasoning_status': 'unverified unless explicit counters are returned',
        'prompt_design': 'typed choice; no visible rationale requested; independent contexts'}
    write_json(out / 'manifest.json', manifest)
    items = {item['id']: item for item in bank['items']}
    cost, failures, started = 0., 0, time.monotonic()
    stop_reason = None
    rows = []
    with (out / 'trace.jsonl').open('x') as trace:
        for index, cell in enumerate(bank['schedule']):
            item, arm = items[cell['item_id']], cell['arm']
            if time.monotonic() - started >= 1200:
                stop_reason = stop_reason or 'batch_deadline'
            if cost + .005 > .20:
                stop_reason = stop_reason or 'spend_reservation_limit'
            if index >= 216:
                stop_reason = stop_reason or 'request_limit'
            if stop_reason:
                row = score(item, arm, {}, 'unstarted: ' + stop_reason)
                row['attempted'] = False
                rows.append(row)
                continue
            body = request(item, arm)
            if len(canonical(body).encode()) > 50000:
                raise RuntimeError('Prompt byte ceiling exceeded')
            req_event = {'kind': 'request', 'index': index, **cell, 'body': body}
            trace.write(canonical(req_event) + '\n'); trace.flush(); os.fsync(trace.fileno())
            t = time.monotonic()
            reply = post(body, key)
            seconds = time.monotonic() - t
            event = {'kind': 'response', 'index': index, **cell, 'seconds': seconds, **reply}
            trace.write(canonical(event) + '\n'); trace.flush(); os.fsync(trace.fileno())
            result = reply.get('response', {})
            row = score(item, arm, result, reply.get('error'))
            row.update(attempted=True, seconds=seconds, request_sha256=digest(body),
                       response_sha256=digest(reply))
            rows.append(row)
            bill = result.get('usage', {}).get('cost')
            if not isinstance(bill, (int, float)) or not math.isfinite(bill) or bill < 0:
                stop_reason = 'unknown_billing'
            else:
                cost += bill
                if bill > .005:
                    stop_reason = 'cost_exceeded_reservation'
            failures = 0 if row['valid'] else failures + 1
            if failures >= 3:
                stop_reason = stop_reason or 'three_consecutive_invalid_responses'
            if (index + 1) % 12 == 0 or stop_reason:
                print(canonical({'completed': index + 1, 'planned': 216,
                    'valid': sum(r['valid'] for r in rows), 'cost_usd': cost,
                    'elapsed_seconds': round(time.monotonic() - started, 1), 'stop': stop_reason}), flush=True)
    manifest.update(stop_reason=stop_reason, billed_cost_usd=cost,
        elapsed_seconds=time.monotonic()-started,
        trace_sha256=sha_file(out/'trace.jsonl'),
        completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    write_json(out/'manifest.json', manifest)
    write_json(out/'rows.json', rows)
    write_json(out/'summary.json', summarize(rows, bank, manifest))
    print(canonical({'done': str(out), 'requests': sum(r['attempted'] for r in rows), 'cost_usd': cost}))


def cluster_ci(rows, value, count=5000):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r['seed']].append(value(r))
    means = [statistics.mean(v) for v in groups.values()]
    rng = random.Random(116)
    samples = sorted(statistics.mean(rng.choices(means, k=len(means))) for _ in range(count))
    return [samples[int(.025*count)], samples[int(.975*count)]]


def stats(rows):
    good = [r for r in rows if r['valid']]
    regrets = [r['root_regret'] for r in good if r.get('root_regret') is not None]
    briers = [r['binary_brier'] for r in good if 'binary_brier' in r]
    return {'n': len(rows), 'valid': len(good), 'correct': sum(r['correct'] for r in rows),
            'accuracy': statistics.mean(r['correct'] for r in rows),
            'accuracy_seed_bootstrap_95': cluster_ci(rows, lambda r: int(r['correct'])),
            'mean_root_regret_valid_only': statistics.mean(regrets) if regrets else None,
            'binary_brier_valid_only': statistics.mean(briers) if briers else None}


def summarize(rows, bank, manifest):
    by_key = {(r['item_id'], r['arm']): r for r in rows}
    paired = []
    for item in bank['items']:
        get = lambda arm: int(by_key[item['id'], arm]['correct'])
        paired.append({'item_id': item['id'], 'seed': item['seed'], 'horizon': item['horizon'],
            'delta': get('assisted') - get('choice'),
            'both_flip_correct': get('choice') * get('flip'),
            'triple_correct': get('choice') * get('flip') * get('sham'),
            'base_correct_sham_wrong': get('choice') * (1 - get('sham'))})
    def pairs(group):
        return {'n': len(group), 'assisted_gain': statistics.mean(x['delta'] for x in group),
            'assisted_gain_seed_bootstrap_95': cluster_ci(group, lambda x: x['delta']),
            'improved': sum(x['delta'] > 0 for x in group),
            'worsened': sum(x['delta'] < 0 for x in group),
            'both_flip_correct': sum(x['both_flip_correct'] for x in group),
            'triple_correct': sum(x['triple_correct'] for x in group),
            'base_correct_sham_wrong': sum(x['base_correct_sham_wrong'] for x in group)}
    latency = sorted(r['seconds'] for r in rows if r.get('attempted'))
    gain = statistics.mean(x['delta'] for x in paired)
    positive_depths = sum(statistics.mean(x['delta'] for x in paired if x['horizon'] == h) > 0 for h in HORIZONS)
    reliable = sum(r['valid'] for r in rows) / len(rows) >= .95
    calibrated = statistics.mean(r['correct'] for r in rows if r['arm'] == 'readout') >= .90
    return {'manifest': manifest, 'verification': verify_bank(bank),
        'by_arm': {a: stats([r for r in rows if r['arm'] == a]) for a in ARMS},
        'by_horizon': {str(h): {a: stats([r for r in rows if r['arm'] == a and r['horizon'] == h]) for a in ARMS} for h in HORIZONS},
        'paired_overall': pairs(paired),
        'paired_by_horizon': {str(h): pairs([x for x in paired if x['horizon'] == h]) for h in HORIZONS},
        'baselines': {'constant_A_accuracy': .5, 'constant_B_accuracy': .5,
            'uniform_random_expected_accuracy': .5, 'exact_oracle_accuracy': 1.,
            'depth2_zero_leaf_search_root_accuracy': .5,
            'independent_random_base_flip_both_correct_expectation': .25,
            'independent_random_triple_correct_expectation': .125},
        'latency_seconds': {'p50': statistics.median(latency) if latency else None,
            'p95': latency[math.ceil(.95*len(latency))-1] if latency else None},
        'usage_totals': {k: sum(r['usage'].get(k, 0) or 0 for r in rows) for k in ('input_tokens', 'output_tokens', 'cost')},
        'models': dict(collections.Counter(r.get('resolved_model') for r in rows if r.get('attempted'))),
        'providers': dict(collections.Counter(r.get('provider') for r in rows if r.get('attempted'))),
        'reasoning_counter_present_calls': sum('reasoning_tokens' in r['usage'] or
            'reasoning_tokens' in r['usage'].get('completion_tokens_details', {}) for r in rows),
        'decision': {'reliable': reliable, 'readout_calibration_passed': calibrated,
            'gain_at_least_15pp': gain >= .15, 'positive_horizons': positive_depths,
            'exploratory_promising_assistance_signal': reliable and calibrated and gain >= .15 and positive_depths >= 2,
            'confirmatory': False},
        'limitations': ['12 independent seed clusters; exploratory only',
            'two disjoint root components; connectivity shortcuts possible',
            'length, input tokens and meaningful transition distance are not independently controlled',
            'no matched irrelevant midpoint annotation control in this pilot',
            'flip/sham edits match changed-entry count but not payoff magnitude or relevance',
            'assistance externally computes future values; question types differ in intrinsic difficulty',
            'missing hidden reasoning counters does not establish zero internal reasoning',
            'no full-plan, online interaction, no-op insertion, or game performance measured']}


def audit(args):
    bank_path, out = Path(args.bank), Path(args.output)
    bank = json.loads(bank_path.read_text())
    manifest = json.loads((out/'manifest.json').read_text())
    rows = json.loads((out/'rows.json').read_text())
    events = [json.loads(line) for line in (out/'trace.jsonl').read_text().splitlines()]
    assert sha_file(bank_path) == manifest['fixture_sha256']
    assert sha_file(out/'trace.jsonl') == manifest['trace_sha256']
    assert make_bank() == bank or canonical(make_bank()) == canonical(bank)
    verify_bank(bank)
    lookup = {x['id']: x for x in bank['items']}
    row_lookup = {(r['item_id'], r['arm']): r for r in rows}
    assert len(rows) == 216 and len(row_lookup) == 216
    for i in range(0, len(events), 2):
        req, res = events[i:i+2]
        assert req['kind'] == 'request' and res['kind'] == 'response'
        assert req['index'] == res['index']
        assert (req['item_id'], req['arm']) == (res['item_id'], res['arm'])
        row = row_lookup[req['item_id'], req['arm']]
        expected_request = request(lookup[req['item_id']], req['arm'])
        assert req['body'] == expected_request
        assert digest(req['body']) == row['request_sha256']
        reply = {k: res[k] for k in ('response', 'error') if k in res}
        assert digest(reply) == row['response_sha256']
        rescored = score(lookup[req['item_id']], req['arm'], res.get('response', {}), res.get('error'))
        assert all(row[k] == v for k, v in rescored.items())
    assert len(events) // 2 == sum(r.get('attempted', False) for r in rows)
    costs = sum(r['usage'].get('cost', 0) or 0 for r in rows)
    assert abs(costs - manifest['billed_cost_usd']) < 1e-10
    expected_summary = summarize(rows, bank, manifest)
    assert json.loads((out/'summary.json').read_text()) == expected_summary
    result = {'passed': True, 'trace_pairs_verified': len(events)//2,
              'fixture_regeneration_identical': True, 'cost_usd': costs,
              'trace_sha256': sha_file(out/'trace.jsonl'), 'fixture_sha256': sha_file(bank_path)}
    write_json(out/'audit.json', result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=('freeze', 'run', 'audit', '_worker'))
    parser.add_argument('--bank', default='experiments/E116/fixtures.json')
    parser.add_argument('--output', default='artifacts/runs/e116-pilot-v1')
    parser.add_argument('--env-file', default=str(ROOT/'.env'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == '_worker':
        worker()
    elif args.command == 'freeze':
        if Path(args.bank).exists():
            raise SystemExit('Refusing to overwrite an existing frozen bank.')
        bank = make_bank()
        verification = verify_bank(bank)
        write_json(args.bank, bank)
        print(canonical({**verification, 'fixture_sha256': sha_file(args.bank)}))
    elif args.command == 'run':
        run(args)
    else:
        audit(args)


if __name__ == '__main__':
    main()
