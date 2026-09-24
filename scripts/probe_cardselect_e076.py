"""One bounded Jev call from E076's frozen card-selection context; no game action."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from rsi.engine import ROOT
from rsi.full import macro_candidates
from rsi.jev import Budget, Jev
from rsi.trace import Trace, version_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['baseline', 'treatment'], required=True)
    args = parser.parse_args()
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before model probe')
    frozen_path = ROOT / 'experiments/E076/frozen-card-select.json'
    raw = frozen_path.read_bytes()
    frozen = json.loads(raw)
    context = frozen['context']
    state = context['state']
    candidates = macro_candidates(state)
    legal_indices = {card['index'] for card in state['cards']}
    legal = True
    for candidate in candidates:
        action = candidate['action']
        if action['action'] == 'skip_select':
            legal &= state['min_select'] == 0
        elif action['action'] == 'select_cards':
            indices = [int(value) for value in action['args']['indices'].split(',')]
            legal &= (state['min_select'] <= len(indices) <= state['max_select']
                      and len(set(indices)) == len(indices) and set(indices) <= legal_indices)
        else:
            legal = False
    trace = Trace(ROOT / 'artifacts/runs' / f'e076-{uuid.uuid4()}',
                  {**manifest, 'experiment': 'E076', 'phase': args.phase, 'scope': 'model_request_only'})
    budget = Budget(max_calls=3, max_usd=.02, conservative_failures=True)
    result = {'schema_version': 1, 'experiment': 'E076', 'phase': args.phase,
              'manifest': manifest, 'frozen_input_sha256': hashlib.sha256(raw).hexdigest(),
              'source_trace_sha256': frozen['source_trace_sha256'],
              'candidate_count': len(candidates),
              'has_skip': any(c['action']['action'] == 'skip_select' for c in candidates),
              'all_candidates_legal': bool(legal)}
    try:
        selected, metadata = Jev(budget).choose(context, candidates, trace)
        result.update(status='accepted', selected_id=selected['id'], selected_action=selected['action'],
                      model=metadata.get('model'), provider_cost_usd=metadata.get('usage',{}).get('cost'))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        result['budget_calls'] = budget.calls
        result['budget_estimated_usd'] = budget.estimated_usd
        result['trace_path'] = str(trace.path.relative_to(ROOT))
        result['trace_sha256'] = trace.close()
    for line in trace.path.read_text().splitlines():
        row = json.loads(line)
        if row['kind'] == 'model_request':
            result['request_bytes'] = len(json.dumps(row['data'], ensure_ascii=False).encode())
            break
    output = ROOT / 'experiments/E076' / f'{args.phase}-result.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key:result.get(key) for key in ['phase','status','error','candidate_count',
                      'has_skip','all_candidates_legal','request_bytes','selected_id','provider_cost_usd',
                      'trace_sha256']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
