"""Bounded read-only recovery after a completed native action's wait times out."""

import time

from .scenes import fingerprint


GAME_THREAD_WAIT_ERROR = "The game thread did not run the posted action in time."


def read_after_accepted_action(mcp, before, expected_run_id, trace, *,
                               timeout=45., interval=.5,
                               clock=time.monotonic, sleep=time.sleep):
    """Never resend the action; accept only a fresh, ready state of the same run."""
    try:
        mcp.call('wait_until_actionable', {'timeout_seconds': 10, 'raw_state': True})
    except RuntimeError as exc:
        if GAME_THREAD_WAIT_ERROR not in str(exc):
            raise
        trace.write('wait_recovery', {'status': 'started', 'error': str(exc),
                                      'before_hash': fingerprint(before)})
        started = clock()
        while True:
            raw = mcp.call('get_raw_game_state')
            if raw.get('run_id') != expected_run_id:
                raise RuntimeError('Game run identity changed during wait recovery')
            if raw.get('screen') in ('PAUSE_MENU', 'SETTINGS'):
                raise RuntimeError('Game paused during wait recovery')
            progressed = fingerprint(raw) != fingerprint(before)
            readiness = (raw.get('combat') or {}).get('action_readiness') or {}
            ready = (raw.get('screen') != 'COMBAT'
                     or (readiness.get('can_use_combat_actions') is True
                         and readiness.get('snapshot_stable') is True))
            if progressed and ready:
                trace.write('wait_recovery', {'status': 'recovered',
                                              'seconds': round(clock() - started, 3),
                                              'after_hash': fingerprint(raw)})
                return raw
            if clock() - started >= timeout:
                trace.write('wait_recovery', {'status': 'timeout',
                                              'seconds': round(clock() - started, 3),
                                              'progressed': progressed, 'ready': ready})
                raise TimeoutError('Native state did not stabilize after accepted action')
            sleep(interval)
    raw = mcp.call('get_raw_game_state')
    if raw.get('run_id') != expected_run_id:
        raise RuntimeError('Game run identity changed after accepted action')
    return raw
