"""Once-per-room Jev recipe transfer, real outcomes, zero-model control."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import random
import time
import uuid

from rsi.engine import ROOT
from rsi.jev import Budget, Jev
from rsi.policy import model_state
from rsi.trace import Trace, digest, version_manifest
from scripts.search_teacher_e096 import battle, file_hash


DIRECTORY = ROOT / 'experiments/E097'


def model_input(entry, lessons=None):
    state = copy.deepcopy(model_state(entry))
    # A seed/hash is only a controller binding, never a strategy feature.
    state.get('context', {}).pop('seed', None)
    payload = {
        'task': 'Choose ONE complete battle policy to execute for this entire Boss room. '
                'The criteria are policy configurations, not individual card actions. '
                'A deterministic executor will use fresh legal actions after selection. '
                'No further model or teacher calls will occur during the battle.',
        'current_state': state,
        'policy_semantics': {
            'legacy': 'existing approximate whole-hand turn planner; fixed score',
            'balanced': 'single-action estimated damage, mitigation, mechanics and efficiency',
            'scaling': 'same single-action policy with larger Power and Doom/summon utility',
            'draw': 'same single-action policy with larger immediate card-draw utility',
            'loss_price': 'HP-loss/marginal-block preference; larger emphasizes HP preservation',
            'early': 'use legal potions early with energy availability and duplicator guards',
            'turn5': 'same guarded potion rule but wait until turn 5',
            'none': 'do not use potions',
        },
    }
    if lessons:
        payload['teacher_lessons'] = lessons
    return payload


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation and lessons before evaluation')
    teacher = json.loads((ROOT / 'experiments/E096/result.json').read_text())
    if not teacher['teacher_gate_passed']:
        raise RuntimeError('Winning teacher has not passed its gate')
    if (manifest['headless_assembly_sha256'], manifest['headless_game_sha256']) != (
            teacher['manifest']['headless_assembly_sha256'], teacher['manifest']['headless_game_sha256']):
        raise RuntimeError('Teacher/student engine mismatch')
    bank = json.loads((DIRECTORY / 'policy-bank.json').read_text())
    entries = json.loads((ROOT / 'artifacts/private/e097-entries.json').read_text())
    all_cases = json.loads((ROOT / 'experiments/E096/fixtures.json').read_text())['cases']
    winners = {w['case_id']: w for w in teacher['winners'] if w['repeatable']}
    cases = [c for c in all_cases if c['id'] in winners]
    for case in cases:
        if digest(entries[case['id']]) != case['entry_hash']:
            raise RuntimeError('Private entry payload does not match frozen state')
    budget = Budget(max_calls=60, max_usd=.05, conservative_failures=True)
    jev = Jev(budget)
    started = time.monotonic()

    def run(job):
        index, case, arm, repetition = job
        trace = Trace(ROOT / 'artifacts/runs' / str(uuid.uuid4()), {
            **manifest, 'experiment': 'E097', 'case_id': case['id'], 'arm': arm,
            'repetition': repetition, 'scope': 'room_policy_selection',
            'entry_hash': case['entry_hash'], 'policy_bank_sha256': file_hash(DIRECTORY / 'policy-bank.json')})
        result = dict(case_id=case['id'], arm=arm, repetition=repetition, status='error')
        try:
            expected = winners[case['id']]['policy']
            profiles = copy.deepcopy(bank['profiles'])
            random.Random(9700 + index * 10 + repetition).shuffle(profiles)
            for i, profile in enumerate(profiles):
                profile['id'] = f'p{i:02}'
            trace.write('candidates', profiles)
            if arm == 'lookup':
                selected = next(c for c in profiles if c['policy'] == expected)
                metadata = {'usage': {'cost': 0}, 'seconds': 0}
            else:
                selected, metadata = jev.choose(model_input(entries[case['id']],
                    bank['lesson_bank'] if arm == 'coached' else None), profiles, trace)
            trace.write('selected_profile', selected)
            result.update(policy=selected['policy'], exact_teacher_policy=selected['policy'] == expected,
                          model_cost_usd=metadata['usage'].get('cost'),
                          decision_seconds=metadata['seconds'], model_answer=metadata.get('answer'),
                          model_version=metadata.get('model'))
            actual = battle(case, selected['policy'], f'{arm}_{repetition}', manifest, experiment='E097')
            result.update(status=actual['status'], final_hp=actual['final_hp'],
                          battle=actual)
            reference = next(r for r in teacher['results'] if
                             r['run_id'] == winners[case['id']]['source_run_id'])
            result['teacher_trajectory_match'] = actual['trajectory_sha256'] == reference['trajectory_sha256']
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            trace.write('failure', result['error'])
        trace.write('summary', result)
        result['selection_trace_path'] = str(trace.path.relative_to(ROOT))
        result['selection_trace_sha256'] = trace.close()
        return result

    jobs = [(i, case, arm, rep) for i, case in enumerate(cases)
            for arm in ('lookup', 'unguided', 'coached')
            for rep in (range(1) if arm == 'lookup' else range(3))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, jobs))
    for r in results:
        r['selection_trace_verified'] = file_hash(ROOT / r['selection_trace_path']) == r['selection_trace_sha256']
    audit = (len(results) == 28 and all(r['selection_trace_verified'] and
             r.get('battle', {}).get('entry_verified') and r.get('battle', {}).get('trace_verified')
             for r in results))
    arms = {}
    for arm in ('lookup', 'unguided', 'coached'):
        subset = [r for r in results if r['arm'] == arm]
        arms[arm] = dict(runs=len(subset), clears=sum(r['status'] == 'boss_clear' for r in subset),
                         exact_teacher_policies=sum(r.get('exact_teacher_policy', False) for r in subset),
                         exact_teacher_trajectories=sum(r.get('teacher_trajectory_match', False) for r in subset),
                         reported_model_usd=sum(r.get('model_cost_usd') or 0 for r in subset),
                         decision_seconds=sum(r.get('decision_seconds', 0) for r in subset),
                         statuses=dict(Counter(r['status'] for r in subset)))
    passed = (audit and arms['coached']['clears'] == 12 and
              arms['coached']['exact_teacher_policies'] >= 10 and budget.spent <= .05)
    output = dict(experiment='E097', manifest=manifest, policy_bank_sha256=file_hash(DIRECTORY / 'policy-bank.json'),
                  results=results, arms=arms, all_entry_trace_checks_passed=audit, gate_passed=passed,
                  total_seconds=round(time.monotonic() - started, 3),
                  budget=dict(calls=budget.calls, spent_usd=budget.spent,
                              uncertain_calls=budget.uncertain_calls, estimated_usd=budget.estimated_usd))
    (DIRECTORY / 'result.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: output[k] for k in ('arms', 'all_entry_trace_checks_passed',
                                           'gate_passed', 'total_seconds', 'budget')}), flush=True)


if __name__ == '__main__':
    main()
