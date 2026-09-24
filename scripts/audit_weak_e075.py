"""Compare E075's frozen observed Weak transitions with static and per-hit forecasts."""
import hashlib
import json
from pathlib import Path

from rsi.numerical import intent_damage, weakened_intent_damage
from rsi.trace import version_manifest


def main():
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation before audit')
    path = Path('experiments/E075/frozen-weak-transitions.json')
    raw = path.read_bytes()
    data = json.loads(raw)
    cases = []
    for case in data['cases']:
        before = {'intents': case['before_intents']}
        observed = intent_damage({'intents': case['after_intents']})
        static = intent_damage(before)
        forecast = weakened_intent_damage(before)
        cases.append({'experiment': case['experiment'], 'run_id': case['run_id'],
                      'after_seq': case['after_seq'], 'before': static, 'observed': observed,
                      'forecast': forecast, 'static_absolute_error': abs(static-observed),
                      'forecast_absolute_error': abs(forecast-observed)})
    static_error = sum(case['static_absolute_error'] for case in cases)
    forecast_error = sum(case['forecast_absolute_error'] for case in cases)
    exact = sum(case['forecast'] == case['observed'] for case in cases)
    output = {'schema_version': 1, 'experiment': 'E075', 'scope': data['scope'],
              'manifest': manifest, 'frozen_dataset_sha256': hashlib.sha256(raw).hexdigest(),
              'source_trace_count': len(data['sources']), 'eligible_count': len(cases),
              'static_absolute_error': static_error, 'forecast_absolute_error': forecast_error,
              'relative_error_reduction': (static_error-forecast_error)/static_error if static_error else None,
              'exact_forecasts': exact, 'exact_fraction': exact/len(cases) if cases else None,
              'mismatches': [case for case in cases if case['forecast'] != case['observed']]}
    Path('experiments/E075/audit-result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: output[key] for key in ['eligible_count','static_absolute_error',
                        'forecast_absolute_error','relative_error_reduction','exact_forecasts',
                        'exact_fraction']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
