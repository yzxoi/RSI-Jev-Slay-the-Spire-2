"""Reconcile every E104 run, resource choice and same-state reconsideration."""
from collections import Counter
import argparse
import hashlib
import json

from rsi.act_trial import advance_history, candidate_set, decision_payload
from rsi.end_turn_recheck import act1_clear, recheck_gate, review_payload
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.policy import model_state
from rsi.resources import inventory, require_resource_interface
from rsi.trace import digest


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_run(result):
    path = ROOT / result['trace_path']
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    wire = path.with_name('wire.jsonl')
    wire_rows = [json.loads(line) for line in wire.read_text().splitlines()]
    commands = [r['data'] for r in wire_rows if r['kind'] == 'command']
    states = [r['data'] for r in wire_rows if r['kind'] == 'state' and r['data'].get('type') != 'ready']
    start = {'cmd': 'start_run', 'character': result['character'], 'seed': result['seed'], 'ascension': 0}
    entry = next(r['data']['state'] for r in rows if r['kind'] == 'entry')
    manifest = rows[0]['data']
    checks = {'trace_hash': file_hash(path) == result['trace_sha256'],
              'wire_hash': file_hash(wire) == result['wire_sha256'],
              'start': commands[0] == start and states[0] == entry and digest(entry) == result['initial_state_hash'],
              'manifest': all(manifest[k] == v for k, v in result['manifest'].items()) and not manifest['tracked_dirty'],
              'resource_mode': manifest['resource_decisions'] is True,
              'no_debug': all(c['cmd'] in ('start_run', 'action') for c in commands),
              'chain': True, 'legal': True, 'model_context': True, 'recheck': True,
              'resources': True, 'stop_boundary': True}
    history = {}
    current = entry
    before = selected = None
    legal = allowed = []
    gate = proposal = None
    phase = None
    answers = {}
    phases = []
    transitions = []
    action_counts = Counter()
    scene_counts = Counter()
    response_counts = Counter()
    failure_counts = Counter()
    phase_costs = Counter()
    phase_seconds = Counter()
    versions = set()
    triggers = rechecks = changes = repeated_ends = 0
    request_count = 0
    boss = False
    events = []
    end_turns = []
    acquisitions = []
    last_resource = None
    for row in rows:
        kind, data = row['kind'], row['data']
        if kind == 'boss_entry':
            context = current.get('context', {})
            checks['stop_boundary'] &= (current.get('decision') == 'combat_play' and context.get('act') == 1
                                        and context.get('room_type') == 'Boss' and data['state_hash'] == digest(current))
            boss = True
        elif kind == 'before':
            before = data['state']
            checks['chain'] &= before == current and digest(before) == data['state_hash']
            checks['stop_boundary'] &= not act1_clear(before, boss) and before.get('decision') != 'game_over'
            require_resource_interface(before)
            legal, allowed, guard = candidate_set(before, history)
            scene_counts[before['decision']] += 1
            phases = []
            answers = {}
            gate = proposal = None
        elif kind == 'candidates':
            checks['legal'] &= data == legal
        elif kind == 'allowed_candidates':
            checks['legal'] &= data == allowed
        elif kind == 'end_turn_guard':
            checks['legal'] &= data == guard
        elif kind == 'request_phase':
            phase = data['phase']
            phases.append(phase)
            checks['model_context'] &= data['state_hash'] == digest(before) and data['step'] == len(transitions)
            checks['recheck'] &= phases in (['initial'], ['initial', 'recheck'])
            if phase == 'recheck':
                checks['recheck'] &= result['arm'] == 'recheck' and bool(gate and gate['eligible'])
        elif kind == 'model_request':
            request_count += 1
            expected = decision_payload(before, history)
            if phase == 'recheck':
                expected = review_payload(expected, proposal, gate)
            criteria = data['questions']['action']['criteria']
            checks['model_context'] &= data['state'] == expected and data['state']['state'] == model_state(before)
            checks['legal'] &= list(criteria) == [c['id'] for c in allowed]
            checks['legal'] &= criteria == {c['id']: {k: v for k, v in c.items() if k != 'id'} for c in allowed}
        elif kind == 'model_response':
            response = data['response']
            response_counts[phase] += 1
            phase_costs[phase] += response.get('usage', {}).get('cost', 0)
            phase_seconds[phase] += data['seconds']
            versions.add(response.get('model'))
            choice_id = response['answers']['action']['choice']
            answers[phase] = next(c for c in allowed if c['id'] == choice_id)
        elif kind == 'model_failure':
            failure_counts[phase] += 1
        elif kind == 'recheck_gate':
            proposal = data['proposal']
            gate = data['gate']
            checks['recheck'] &= (data['state_hash'] == digest(before) and proposal == answers['initial']
                                  and gate == recheck_gate(before, proposal, allowed))
            triggers += int(gate['eligible'])
        elif kind == 'recheck_result':
            rechecks += 1
            changes += int(data['final'] != data['initial'])
            repeated_ends += int(data['final']['action']['action'] == 'end_turn')
            checks['recheck'] &= (data['state_hash'] == digest(before) and data['initial'] == proposal
                                  and data['final'] == answers['recheck'] and phases == ['initial', 'recheck'])
            events.append({'step': len(transitions), 'state_hash': digest(before),
                           'floor': before.get('context', {}).get('floor'), 'round': before.get('round'),
                           'hp': before['player']['hp'], 'preview': gate['preview'],
                           'initial': proposal, 'final': data['final']})
        elif kind == 'selected':
            selected = data['choice']
            checks['legal'] &= selected in allowed
            source = data['source']
            if source == 'only_legal_choice':
                checks['legal'] &= len(allowed) == 1 and not phases
            elif source == 'free_potion_claim':
                checks['resources'] &= before['decision'] == 'potion_reward' and before['can_claim'] and not phases
                checks['resources'] &= selected['action']['action'] == 'claim_potion_reward'
            else:
                expected_review = result['arm'] == 'recheck' and gate['eligible']
                checks['recheck'] &= phases == (['initial', 'recheck'] if expected_review else ['initial'])
                checks['recheck'] &= source == ('jev_recheck' if expected_review else 'jev')
                checks['legal'] &= selected == answers['recheck' if expected_review else 'initial']
        elif kind == 'after':
            current = data['state']
            i = len(transitions) + 1
            checks['chain'] &= commands[i] == selected['action'] and states[i] == current and digest(current) == data['state_hash']
            transitions.append([digest(before), selected['action'], digest(current)])
            action_counts[selected['action']['action']] += 1
            last_resource = {'action': selected['action'], 'before': inventory(before), 'after': inventory(current),
                             'gold_before': before['player'].get('gold'), 'gold_after': current['player'].get('gold')}
            advance_history(history, before, selected)
            if selected['action']['action'] == 'end_turn':
                end_turns.append({'step': len(transitions) - 1, 'floor': before.get('context', {}).get('floor'),
                                  'round': before.get('round'), 'energy': before.get('energy'),
                                  'hp_before': before['player']['hp'], 'hp_after': current['player']['hp'],
                                  'net_hp_loss': before['player']['hp'] - current['player']['hp']})
            if selected['action']['action'] in ('select_card_reward', 'skip_card_reward', 'buy_card', 'buy_relic', 'buy_potion',
                                                'claim_potion_reward', 'skip_potion_reward', 'discard_potion', 'use_potion'):
                acquisitions.append({'step': len(transitions) - 1, 'floor': before.get('context', {}).get('floor'),
                                     'decision': before['decision'], 'choice': selected})
        elif kind == 'resource_transition':
            checks['resources'] &= data == last_resource
    checks['counts'] = (len(transitions) == result['steps'] and len(commands) == len(states) == len(transitions) + 1
                        and dict(action_counts) == result['action_counts'] and dict(scene_counts) == result['scene_counts'])
    checks['trajectory'] = digest(transitions) == result['trajectory_sha256'] and digest(current) == result['final_state_hash']
    checks['recheck_counts'] = ((triggers, rechecks, changes, repeated_ends) ==
                               (result['triggers'], result['rechecks'], result['changed_choices'], result['repeated_end_turns']))
    calls = sum(response_counts.values()) + sum(failure_counts.values())
    cost = sum(phase_costs.values())
    checks['usage'] = (calls == result['model_calls'] and sum(failure_counts.values()) == result['unknown_model_calls']
                       and abs(cost - result['model_cost_usd']) < 1e-9
                       and abs(cost + sum(failure_counts.values()) * Budget.reserve_usd - result['budgeted_usd']) < 1e-9)
    checks['request_count'] = request_count == calls or (request_count == calls + 1 and result['status'] == 'budget_exhausted')
    checks['stop_boundary'] &= boss == result['boss_entered']
    if result['status'] == 'act1_clear':
        checks['stop_boundary'] &= act1_clear(current, boss)
    elif result['status'] == 'normal_defeat':
        checks['stop_boundary'] &= current.get('decision') == 'game_over' and not current.get('victory')
    else:
        checks['stop_boundary'] &= result['status'] in ('error', 'budget_exhausted')
    log = path.with_name('engine.stderr.log')
    checks['engine_log'] = file_hash(log) == result['engine_log_sha256']
    checks['stop_boundary'] &= b'forcing game_over' not in log.read_bytes() or result['status'] == 'error'
    return {'run_id': result['run_id'], 'checks': checks, 'passed': all(checks.values()),
            'returned_models': sorted(versions), 'phase_responses': dict(response_counts),
            'phase_failures': dict(failure_counts), 'phase_cost_usd': dict(phase_costs),
            'phase_seconds': dict(phase_seconds), 'recheck_events': events,
            'end_turn_analysis': {'count': len(end_turns),
                                 'hp_loss_at_zero_energy': sum(max(0, e['net_hp_loss']) for e in end_turns if e['energy'] == 0),
                                 'hp_loss_with_energy_remaining': sum(max(0, e['net_hp_loss']) for e in end_turns if e['energy'] > 0),
                                 'turns': end_turns}, 'resource_and_reward_choices': acquisitions}


def first_divergence(pair):
    paths = {}
    first_changed_review = None
    for arm, result in pair.items():
        rows = [json.loads(line) for line in (ROOT / result['trace_path']).read_text().splitlines()]
        transitions = []
        before = selected = None
        for row in rows:
            if row['kind'] == 'before':
                before = row['data']['state_hash']
            elif row['kind'] == 'selected':
                selected = row['data']['choice']['action']
            elif row['kind'] == 'after':
                transitions.append([before, selected, row['data']['state_hash']])
            elif arm == 'recheck' and row['kind'] == 'recheck_result' and first_changed_review is None:
                if row['data']['initial'] != row['data']['final']:
                    first_changed_review = len(transitions)
        paths[arm] = transitions
    a, b = paths['baseline'], paths['recheck']
    index = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if index is None and len(a) != len(b):
        index = min(len(a), len(b))
    return {'first_divergent_step': index, 'first_changed_recheck_step': first_changed_review,
            'diverged_before_changed_recheck': index is not None and (first_changed_review is None or index < first_changed_review),
            'note': 'Descriptive unmatched-sampling diagnostic; does not estimate a causal effect.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iteration', choices=['i01', 'i02'], default='i01')
    args = parser.parse_args()
    directory = ROOT / 'experiments/E104'
    inputs = json.loads((directory / 'inputs.json').read_text())
    report = json.loads((ROOT / f'artifacts/runs/e104-{args.iteration}-results.json').read_text())
    audits = [audit_run(r) for r in report['results']]
    selection = (file_hash(directory / 'inputs.json') == report['inputs_sha256']
                 and [{k: r[k] for k in c} for c, r in zip(inputs['configs'], report['results'], strict=True)] == inputs['configs'])
    pairs = []
    for seed in ('e104_unknown_001', 'e104_unknown_002'):
        for character in ('Ironclad', 'Silent'):
            pair = {r['arm']: r for r in report['results'] if r['seed'] == seed and r['character'] == character}
            same_start = pair['baseline']['initial_state_hash'] == pair['recheck']['initial_state_hash']
            pairs.append({'seed': seed, 'character': character, 'same_start': same_start,
                          'baseline_status': pair['baseline']['status'], 'recheck_status': pair['recheck']['status'],
                          **first_divergence(pair)})
    usage = all(abs(sum(r[key] for r in report['results']) - report['session'][key]) < 1e-9
                for key in ('model_calls', 'model_cost_usd', 'unknown_model_calls', 'budgeted_usd'))
    prior = report.get('prior_cohort')
    prior_calls = prior['session']['model_calls'] if prior else 0
    prior_usd = prior['session']['budgeted_usd'] if prior else 0
    budget_valid = (prior_calls + report['session']['model_calls'] <= inputs['session_max_attempts']
                    and prior_usd + report['session']['budgeted_usd'] <= inputs['session_max_usd'])
    if args.iteration == 'i02':
        budget_valid &= bool(prior) and file_hash(ROOT / prior['path']) == prior['sha256']
    out = {'experiment': 'E104', 'iteration': args.iteration, 'input_selection': selection, 'session_usage': usage,
           'combined_budget_valid': budget_valid, 'pairs': pairs, 'runs': audits,
           'all_passed': selection and usage and budget_valid and all(a['passed'] for a in audits) and all(p['same_start'] for p in pairs)}
    report['summary'] = {arm: {'act1_clears': sum(r['status'] == 'act1_clear' for r in report['results'] if r['arm'] == arm),
                              'runs': sum(r['arm'] == arm for r in report['results']),
                              **{key: sum(r[key] for r in report['results'] if r['arm'] == arm)
                                 for key in ('model_calls', 'model_cost_usd', 'unknown_model_calls', 'triggers', 'rechecks', 'changed_choices', 'repeated_end_turns')}}
                         for arm in ('baseline', 'recheck')}
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    (directory / 'audit.json').write_text(json.dumps(out, indent=2) + '\n')
    cohort_directory = directory / ('iteration-02' if args.iteration == 'i02' else 'iteration-01')
    cohort_directory.mkdir(exist_ok=True)
    (cohort_directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    (cohort_directory / 'audit.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'all_passed': out['all_passed'], 'summary': report['summary'],
                      'failed_checks': [{'run_id': a['run_id'], 'checks': [k for k, v in a['checks'].items() if not v]}
                                        for a in audits if not a['passed']]}, indent=2))


if __name__ == '__main__':
    main()
