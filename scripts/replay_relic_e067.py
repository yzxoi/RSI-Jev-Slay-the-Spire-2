"""Replay one frozen E066 shop prefix and its advertised relic purchase."""
import argparse
import json
from pathlib import Path
import uuid

from rsi.engine import ROOT, Headless
from rsi.trace import Trace, digest, version_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit replay implementation before execution')
    fixture = json.loads(Path(args.fixture).read_text())
    trace = Trace(ROOT / 'artifacts/runs' / str(uuid.uuid4()),
                  {**manifest, 'scope': 'E067_relic_purchase_replay', 'fixture': args.fixture})
    result = {'status': 'error', 'character': fixture['character'], 'ascension': fixture['ascension'],
              'seed': fixture['seed'], 'prefix_actions': 0, 'expected_state_hash': fixture['pre_purchase_state_hash'],
              'purchase_action': fixture['purchase_action']}
    engine = None
    state = {}
    try:
        engine = Headless(trace.directory)
        state = engine.send({'cmd': 'start_run', 'character': fixture['character'],
                             'ascension': fixture['ascension'], 'seed': fixture['seed']})
        for action in fixture['prefix_actions']:
            state = engine.send(action)
            result['prefix_actions'] += 1
        result['before_state_hash'] = digest(state)
        if result['before_state_hash'] != fixture['pre_purchase_state_hash']:
            raise RuntimeError('Frozen prefix did not reach the expected shop state')
        index = fixture['purchase_action']['args']['relic_index']
        relic = state['relics'][index]
        result['relic_name'] = relic['name']
        result['relic_price'] = relic['cost']
        result['gold_before'] = state['player']['gold']
        result['relics_before'] = [r['name'] for r in state['player']['relics']]
        trace.write('before_purchase', {'state_hash': result['before_state_hash'],
                                        'gold': result['gold_before'], 'relic': relic})
        state = engine.send(fixture['purchase_action'])
        result['gold_after'] = state['player']['gold']
        result['relics_after'] = [r['name'] for r in state['player']['relics']]
        result['after_state_hash'] = digest(state)
        result['price_paid'] = result['gold_before'] - result['gold_after']
        result['relic_acquired'] = result['relic_name'] in result['relics_after']
        result['status'] = ('compatible' if result['price_paid'] == result['relic_price']
                            and result['relic_acquired'] else 'state_mismatch')
        trace.write('after_purchase', {'state_hash': result['after_state_hash'],
                                       'gold': result['gold_after'], 'relics': result['relics_after']})
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', {'error': result['error']})
    finally:
        if engine:
            engine.close()
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'manifest': manifest, 'result': result}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'trace_path'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
