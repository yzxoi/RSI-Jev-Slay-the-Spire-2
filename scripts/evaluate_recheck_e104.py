from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from rsi.act_trial import episode
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.trace import version_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iteration', choices=['i01', 'i02'], required=True)
    parser.add_argument('--prior-report', type=Path)
    args = parser.parse_args()
    inputs = ROOT / 'experiments/E104/inputs.json'
    config = json.loads(inputs.read_text())
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise ValueError('Commit before testing')
    if manifest['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise ValueError('Wrong game build')
    prior = None
    prior_calls = 0
    prior_usd = 0
    if args.iteration == 'i02':
        if args.prior_report is None:
            raise ValueError('Iteration 2 requires the preserved first-cohort report')
        expected = ROOT / 'experiments/E104/iteration-01/result.json'
        if args.prior_report.resolve() != expected.resolve():
            raise ValueError('Use the committed complete first-cohort report')
        earlier = json.loads(expected.read_text())
        assert len(earlier['results']) == 8 and earlier['inputs_sha256'] == hashlib.sha256(inputs.read_bytes()).hexdigest()
        prior_calls = earlier['session']['model_calls']
        prior_usd = earlier['session']['budgeted_usd']
        prior = {'path': str(expected.relative_to(ROOT)), 'sha256': hashlib.sha256(expected.read_bytes()).hexdigest(),
                 'session': earlier['session']}
    target = ROOT / f'artifacts/runs/e104-{args.iteration}-results.json'
    index = ROOT / f'artifacts/runs/e104-{args.iteration}-runs.json'
    if target.exists() or index.exists():
        raise ValueError('Cohort label already exists; do not overwrite earlier runs')
    session = Budget(config['session_max_attempts'] - prior_calls, config['session_max_usd'] - prior_usd,
                     conservative_failures=True)
    configs = [{**c, 'run_id': str(uuid.uuid4())} for c in config['configs']]
    index.write_text(json.dumps(configs, indent=2) + '\n')
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures = [pool.submit(episode, c, manifest, session) for c in configs]
        results = [f.result() for f in futures]
    report = {'experiment': 'E104', 'iteration': args.iteration, 'prior_cohort': prior,
              'manifest': manifest, 'inputs_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
              'results': results, 'session': {'model_calls': session.calls, 'model_cost_usd': session.spent - session.estimated_usd,
                                             'unknown_model_calls': session.uncertain_calls, 'budgeted_usd': session.spent}}
    target.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
