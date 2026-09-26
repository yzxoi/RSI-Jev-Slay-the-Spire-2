from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import uuid

from rsi.act_trial import episode
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.trace import version_manifest


def main():
    inputs = ROOT / 'experiments/E104/inputs.json'
    config = json.loads(inputs.read_text())
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise ValueError('Commit before testing')
    if manifest['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise ValueError('Wrong game build')
    session = Budget(config['session_max_attempts'], config['session_max_usd'], conservative_failures=True)
    configs = [{**c, 'run_id': str(uuid.uuid4())} for c in config['configs']]
    (ROOT / 'artifacts/runs/e104-runs.json').write_text(json.dumps(configs, indent=2) + '\n')
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures = [pool.submit(episode, c, manifest, session) for c in configs]
        results = [f.result() for f in futures]
    report = {'experiment': 'E104', 'manifest': manifest, 'inputs_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
              'results': results, 'session': {'model_calls': session.calls, 'model_cost_usd': session.spent - session.estimated_usd,
                                             'unknown_model_calls': session.uncertain_calls, 'budgeted_usd': session.spent}}
    (ROOT / 'artifacts/runs/e104-results.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
