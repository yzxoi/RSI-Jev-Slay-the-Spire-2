"""One verified room-opening action followed by bounded Jev guidance."""
import json
from pathlib import Path

from .scenes import candidates, fingerprint


def load_room_plan(path, raw):
    plan = json.loads(Path(path).read_text())
    required = {'schema_version', 'run_id', 'floor', 'start_state_hash',
                'opening_action', 'guidance'}
    if set(plan) != required or plan['schema_version'] != 1:
        raise ValueError('Invalid room plan schema')
    if not isinstance(plan['floor'], int) or not isinstance(plan['guidance'], str) or not 1 <= len(plan['guidance']) <= 2000:
        raise ValueError('Invalid room plan floor or guidance')
    if (raw.get('run_id') != plan['run_id'] or raw.get('screen') != 'COMBAT'
            or (raw.get('run') or {}).get('floor') != plan['floor']
            or fingerprint(raw) != plan['start_state_hash']):
        raise ValueError('Room plan does not match current combat state')
    if plan['opening_action'] not in [c['action'] for c in candidates(raw)]:
        raise ValueError('Room opener is not currently legal')
    return plan


class RoomPlanSession:
    def __init__(self, plan):
        self.plan = plan
        self.applied = False

    def opening(self, raw, legal):
        if self.applied:
            raise ValueError('Room opener was already accepted')
        if fingerprint(raw) != self.plan['start_state_hash']:
            raise ValueError('Room opener state changed before execution')
        return next((c for c in legal if c['action'] == self.plan['opening_action']),
                    None)

    def accepted(self):
        if self.applied:
            raise ValueError('Room opener was already accepted')
        self.applied = True


def room_context(plan, raw):
    if plan is None or (raw.get('run') or {}).get('floor') != plan['floor']:
        return {}
    return {'room_plan': {'scope': f"combat and rewards on floor {plan['floor']}",
                          'guidance': plan['guidance']}}


def room_complete(plan, raw, actions):
    return bool(plan and actions > 0 and raw.get('screen') == 'MAP'
                and (raw.get('run') or {}).get('floor') >= plan['floor'])
