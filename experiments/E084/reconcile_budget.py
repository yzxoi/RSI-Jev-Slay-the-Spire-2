"""Correct E084's post-run cost labels without rerunning the fixed cohort."""

import json
from pathlib import Path


path = Path(__file__).with_name('result.json')
result = json.loads(path.read_text(encoding='utf-8'))
budget = result['budget']
if 'provider_cost_usd' in budget:
    budget['budgeted_spend_usd'] = budget.pop('provider_cost_usd')
budget['provider_reported_cost_usd'] = sum(run['cost_usd'] for run in result['results'])
assert abs(
    budget['budgeted_spend_usd']
    - budget['provider_reported_cost_usd']
    - budget['estimated_usd']
) < 1e-9
path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
