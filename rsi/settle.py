"""Bounded read-only native turn-start settling. Never retries a game action."""
import time
from .scenes import fingerprint
from .trace import digest


def turn_key(raw):
    if raw.get('screen') != 'COMBAT' or raw.get('selection'): return None
    return (raw.get('run_id'), (raw.get('run') or {}).get('floor'), raw.get('turn'))


def settle_turn(mcp, raw, trace, *, quiet_seconds=.6, min_seconds=.75,
                timeout=8., interval=.15, clock=time.monotonic, sleep=time.sleep):
    if turn_key(raw) is None: return raw
    run_id = raw.get('run_id'); started = clock(); unchanged_since = None; last = None; probes = 0
    while True:
        now = clock(); probes += 1
        if raw.get('run_id') != run_id: raise RuntimeError('Run changed while settling native turn')
        if turn_key(raw) is None:
            trace.write('turn_settle', {'outcome':'scene_changed','seconds':now-started,'probes':probes})
            return raw
        ready = bool((raw.get('combat') or {}).get('action_readiness', {}).get('can_use_combat_actions'))
        signature = digest({'state':fingerprint(raw),'available_actions':raw.get('available_actions')})
        if not ready or signature != last: unchanged_since = now if ready else None
        last = signature
        trace.write('turn_settle_probe', {'elapsed':now-started,'ready':ready,'state_hash':signature,
                    'hand_count':len((raw.get('combat') or {}).get('hand',[])),'turn':raw.get('turn')})
        if ready and unchanged_since is not None and now-unchanged_since >= quiet_seconds and now-started >= min_seconds:
            trace.write('turn_settle', {'outcome':'stable','seconds':now-started,'probes':probes,'state_hash':signature})
            return raw
        if now-started >= timeout:
            trace.write('turn_settle', {'outcome':'timeout','seconds':now-started,'probes':probes})
            raise TimeoutError('Native turn did not settle before deadline; no action sent')
        sleep(min(interval, timeout-(now-started)))
        raw = mcp.call('get_raw_game_state')
