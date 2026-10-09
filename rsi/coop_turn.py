"""Read-only co-op turn wait, bounded by the enclosing run instead of one turn."""

import time
from pathlib import Path

from .multiplayer_guard import require_local_multiplayer


def wait_for_local_action(mcp, raw, trace, *, expected_run_id, local_player_id,
                          player_count, deadline, stop_file=None, interval=.5,
                          clock=time.monotonic, sleep=time.sleep):
    """Return (fresh state, outcome); never assume a peer turn finishes in 8 s."""
    started = clock()
    probes = 0
    while True:
        probes += 1
        if raw.get('run_id') != expected_run_id:
            raise RuntimeError('Game run identity changed while waiting for local turn')
        require_local_multiplayer(raw, expected_player_count=player_count,
                                  expected_local_id=local_player_id)
        if raw.get('screen') != 'COMBAT' or raw.get('selection'):
            outcome = 'scene_changed'
        else:
            readiness = (raw.get('combat') or {}).get('action_readiness') or {}
            outcome = ('local_ready' if readiness.get('can_use_combat_actions') is True and
                       readiness.get('snapshot_stable') is True else None)
        if outcome is None and stop_file and Path(stop_file).exists():
            outcome = 'requested_boundary'
        if outcome is None and clock() >= deadline:
            outcome = 'budget_boundary'
        if outcome:
            trace.write('coop_turn_wait', {'outcome': outcome,
                                          'seconds': round(clock() - started, 3),
                                          'probes': probes})
            return raw, outcome
        sleep(min(interval, max(0, deadline - clock())))
        raw = mcp.call('get_raw_game_state')
