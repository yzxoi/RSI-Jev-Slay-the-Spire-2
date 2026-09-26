"""Keep an experimental co-op controller bound to its own local player."""


def require_local_multiplayer(raw, *, expected_player_count, expected_local_id=None):
    session = raw.get('session') or {}
    multiplayer = raw.get('multiplayer') or {}
    if (session.get('mode'), session.get('phase'), session.get('control_scope')) != (
        'multiplayer', 'run', 'local_player'
    ) or not multiplayer.get('is_multiplayer'):
        raise RuntimeError('Expected a local-player multiplayer run')
    local_id = multiplayer.get('local_player_id')
    if not local_id or (expected_local_id is not None and local_id != expected_local_id):
        raise RuntimeError('Local multiplayer player identity changed')
    if multiplayer.get('player_count') != expected_player_count:
        raise RuntimeError('Multiplayer player count changed')
    for label, players in (
        ('run', (raw.get('run') or {}).get('players')),
        ('combat', (raw.get('combat') or {}).get('players') if raw.get('screen') == 'COMBAT' else None),
    ):
        if players is None:
            if label == 'run':
                raise RuntimeError('Run player roster is missing')
            continue
        own = [player for player in players if player.get('is_local')]
        if len(players) != expected_player_count or len(own) != 1 or own[0].get('player_id') != local_id:
            raise RuntimeError(f'{label} local player ownership is ambiguous')
        if own[0].get('is_connected') is False or own[0].get('is_alive') is False:
            raise RuntimeError(f'{label} local player is unavailable')
    return local_id
