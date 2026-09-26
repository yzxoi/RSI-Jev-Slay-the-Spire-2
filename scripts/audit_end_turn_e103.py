"""Read-only reconciliation of E103 branches and the complete E102 source selection."""
import argparse
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT, action
from rsi.end_turn_check import arithmetic, boundary, branch_plans, fresh_discard, outcome
from rsi.full import macro_candidates
from rsi.policy import combat_candidates
from rsi.trace import digest


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_branch(result, case, prefix, manifest):
    checks = {}
    try:
        path = ROOT / result['trace_path']
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        wire = path.with_name('wire.jsonl')
        wire_rows = [json.loads(line) for line in wire.read_text().splitlines()]
        commands = [r['data'] for r in wire_rows if r['kind'] == 'command']
        states = [r['data'] for r in wire_rows if r['kind'] == 'state' and r['data'].get('type') != 'ready']
        n = len(prefix)
        entry = next(r['data']['state'] for r in rows if r['kind'] == 'entry')
        plan = result['plan']
        checks.update(hashes=file_hash(path) == result['trace_sha256'] and file_hash(wire) == result['wire_sha256'],
                      prefix=commands[:n] == prefix, entry=digest(entry) == case['entry_hash'] == digest(states[n - 1]),
                      no_debug=all(c.get('cmd') in ('start_run', 'action') for c in commands),
                      counts=len(commands) == len(states) == n + len(result['actions']),
                      cap=len(result['actions']) <= 3 and result['seconds'] <= 60,
                      chain=True, legal=True, plan=plan in branch_plans(entry)['plans'])
        recorded_manifest = rows[0]['data']
        checks['manifest'] = all(recorded_manifest[k] == v for k, v in manifest.items()) and not manifest['tracked_dirty']
        current = entry
        before = selected = None
        index = 0
        for row in rows:
            kind, data = row['kind'], row['data']
            if kind == 'before':
                before = data['state']
                checks['chain'] &= before == current and digest(before) == data['state_hash']
            elif kind == 'selected':
                selected = data
                choices = combat_candidates(before) if before['decision'] == 'combat_play' else macro_candidates(before)
                checks['legal'] &= selected in [c['action'] for c in choices]
                if index == 0:
                    checks['plan'] &= selected == plan['first_action']
                elif before['decision'] == 'card_select':
                    checks['plan'] &= selected == fresh_discard(before, plan)
                else:
                    checks['plan'] &= selected == action('end_turn')
            elif kind == 'after':
                current = data['state']
                checks['chain'] &= (current == states[n + index] and digest(current) == data['state_hash']
                                    and selected == commands[n + index] == result['actions'][index])
                index += 1
        checks['counts'] &= index == len(result['actions'])
        checks['outcome'] = (result['status'] == boundary(current, entry)
                             and outcome(current) == result['outcome'] and digest(current) == result['after_hash'])
        checks['original_baseline'] = plan['id'] != 'actual_end' or digest(current) == case['actual_after_hash']
        checks['zero_model_requests'] = not any(r['kind'].startswith('model_') for r in rows)
        return {'probe_id': result['probe_id'], 'checks': checks, 'passed': all(checks.values())}
    except Exception as exc:
        return {'probe_id': result['probe_id'], 'checks': checks, 'passed': False,
                'error': f'{type(exc).__name__}: {exc}'}


def source_selection(source_root, fixtures):
    report = json.loads((ROOT / 'experiments/E102/result.json').read_text())
    found = {}
    for run in report['results']:
        path = source_root / run['trace_path']
        assert file_hash(path) == run['trace_sha256']
        prefix = list(fixtures[run['case']]['commands'])
        state = choice = None
        for line in path.read_text().splitlines():
            row = json.loads(line)
            kind, data = row['kind'], row['data']
            if kind == 'before':
                state = data['state']
            elif kind == 'selected':
                choice = data['choice']['action']
            elif kind == 'after':
                if choice['action'] == 'end_turn' and state.get('energy', 0) > 0:
                    ident = f"{run['case']}-{run['arm']}-r{state['round']:02}"
                    found[ident] = {'state': state, 'prefix': list(prefix), 'after_hash': digest(data['state']),
                                    'trace_sha256': run['trace_sha256']}
                prefix.append(choice)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    directory = ROOT / 'experiments/E103'
    source = directory / 'inputs.json'
    inputs = json.loads(source.read_text())
    report = json.loads((ROOT / 'artifacts/runs/e103-results.json').read_text())
    fixture_path = ROOT / 'experiments/E099/fixtures.json'
    fixtures = {c['id']: c for c in json.loads(fixture_path.read_text())['cases']}
    actual = source_selection(args.source_root, fixtures)
    source_valid = (file_hash(source) == report['inputs_sha256']
                    and file_hash(fixture_path) == inputs['initial_fixtures_sha256']
                    and file_hash(ROOT / 'experiments/E102/result.json') == inputs['source_results_sha256']
                    and set(actual) == {c['id'] for c in inputs['cases']})
    branch_audits = []
    case_audits = []
    for case, result in zip(inputs['cases'], report['cases'], strict=True):
        prefix = fixtures[case['case']]['commands'] + case['continuation_prefix']
        recorded = actual[case['id']]
        source_valid &= (prefix == recorded['prefix'] and case['state'] == recorded['state']
                         and case['actual_after_hash'] == recorded['after_hash']
                         and case['source_trace_sha256'] == recorded['trace_sha256'])
        expected = branch_plans(case['state'])
        checks = {'id': result['id'] == case['id'], 'all_branches': [b['plan'] for b in result['branches']] == expected['plans'],
                  'no_truncation': result['truncated'] == 0 == expected['truncated'], 'arithmetic': True}
        for key, plating in [('visible_arithmetic', False), ('plating_arithmetic', True)]:
            recomputed = arithmetic(case['state'], plating)
            checks['arithmetic'] &= all(v == result[key][k] for k, v in recomputed.items() if k != 'seconds')
        audits = [audit_branch(b, case, prefix, report['manifest']) for b in result['branches']]
        branch_audits.extend(audits)
        complete = all(b['status'] != 'error' for b in result['branches']) and not result['truncated']
        checks['complete'] = result['complete'] == complete
        if complete:
            gain = max(b['outcome']['hp'] for b in result['branches']) - result['branches'][0]['outcome']['hp']
            checks['hp_gain'] = result['best_hp_gain'] == gain and result['flags_missed_defense'] == (gain > 0)
        checks['branches_passed'] = all(a['passed'] for a in audits)
        case_audits.append({'case': case['id'], 'checks': checks, 'passed': all(checks.values())})
    out = {'experiment': 'E103', 'complete_source_selection': source_valid,
           'branches': branch_audits, 'cases': case_audits,
           'all_passed': source_valid and all(c['passed'] for c in case_audits)}
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    (directory / 'audit.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'all_passed': out['all_passed'], 'complete_source_selection': source_valid,
                      'branches': len(branch_audits),
                      'failures': [a for a in branch_audits + case_audits if not a['passed']]}, indent=2))


if __name__ == '__main__':
    main()
