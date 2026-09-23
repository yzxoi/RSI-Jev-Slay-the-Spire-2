"""State-bound, one-floor expert guidance for the native controller."""
import json
from pathlib import Path

from .scenes import fingerprint


def load_floor_plan(path, raw):
    plan = json.loads(Path(path).read_text())
    required = {'schema_version', 'run_id', 'start_floor', 'target_floor',
                'start_state_hash', 'guidance'}
    if set(plan) != required or plan['schema_version'] != 1:
        raise ValueError('Invalid floor plan schema')
    if not isinstance(plan['start_floor'], int) or plan['target_floor'] != plan['start_floor'] + 1:
        raise ValueError('Floor plan must cover exactly one next floor')
    if not isinstance(plan['guidance'], str) or not 1 <= len(plan['guidance']) <= 2000:
        raise ValueError('Floor plan guidance must be 1..2000 characters')
    if (raw.get('run_id') != plan['run_id'] or raw.get('screen') != 'MAP'
            or (raw.get('run') or {}).get('floor') != plan['start_floor']
            or fingerprint(raw) != plan['start_state_hash']):
        raise ValueError('Floor plan does not match the current map state')
    return plan


def plan_context(plan, raw):
    floor = (raw.get('run') or {}).get('floor')
    if plan is None or floor not in (plan['start_floor'], plan['target_floor']):
        return {}
    return {'floor_plan': {'scope': f"map floor {plan['start_floor']} through room floor {plan['target_floor']}",
                           'guidance': plan['guidance']}}


def plan_complete(plan, raw, actions):
    return bool(plan and actions > 0 and raw.get('screen') == 'MAP'
                and (raw.get('run') or {}).get('floor', -1) >= plan['target_floor'])
