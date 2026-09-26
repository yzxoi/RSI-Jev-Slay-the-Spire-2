"""Coordinate one local multiplayer map vote with observed peer state."""

import time


def route_candidates(raw):
    nodes = (raw.get('map') or {}).get('available_nodes') or []
    if (raw.get('session') or {}).get('mode') != 'multiplayer':
        return nodes
    if (raw.get('map') or {}).get('local_vote') is not None:
        return []
    return [node for node in nodes if node.get('vote_count', 0) > 0 and not node.get('has_local_vote')]


def waiting_for_peer_route(raw):
    return (raw.get('screen') == 'MAP' and
            (raw.get('session') or {}).get('mode') == 'multiplayer' and
            not route_candidates(raw))


def wait_for_map_vote_ack(mcp, before, action, trace, *, timeout=10., interval=.2,
                          clock=time.monotonic, sleep=time.sleep):
    nodes = (before.get('map') or {}).get('available_nodes') or []
    index = action.get('option_index')
    target = next((node for node in nodes if node.get('index') == index), None)
    if target is None:
        raise RuntimeError('Submitted map target is absent from the pre-action state')
    coord = (target.get('row'), target.get('col'))
    initial_node = (before.get('map') or {}).get('current_node')
    initial_floor = (before.get('run') or {}).get('floor')
    started = clock()
    while True:
        fresh = mcp.call('get_raw_game_state')
        if fresh.get('run_id') != before.get('run_id'):
            raise RuntimeError('Run changed while waiting for local map vote')
        current_map = fresh.get('map') or {}
        vote = current_map.get('local_vote') or {}
        moved = (fresh.get('screen') != 'MAP' or
                 (fresh.get('run') or {}).get('floor') != initial_floor or
                 current_map.get('current_node') != initial_node)
        if moved or (vote.get('row'), vote.get('col')) == coord:
            trace.write('map_vote_ack', {'outcome': 'transition' if moved else 'local_vote',
                                         'target': {'row': coord[0], 'col': coord[1]},
                                         'seconds': round(clock() - started, 3)})
            return fresh
        if clock() - started >= timeout:
            trace.write('map_vote_ack', {'outcome': 'unconfirmed',
                                         'target': {'row': coord[0], 'col': coord[1]},
                                         'seconds': round(clock() - started, 3)})
            raise RuntimeError('Map vote was not observed; refusing to resend')
        sleep(interval)
