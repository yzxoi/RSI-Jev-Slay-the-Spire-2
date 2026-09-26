"""Bounded offline defense comparisons, never an automatic action override."""
import hashlib
import time
import uuid

from .engine import ROOT, Headless, action
from .full import macro_candidates
from .numerical import intent_damage
from .policy import combat_candidates
from .teacher import terminal
from .trace import Trace, digest

DEFENDS = {'CARD.DEFEND_IRONCLAD', 'CARD.DEFEND_SILENT'}


def branch_plans(state, limit=8):
    if state.get('decision') != 'combat_play':
        raise ValueError('Expected a player-turn decision')
    cards = {c['index']: c for c in state['hand']}
    alternatives = []
    for choice in combat_candidates(state):
        command = choice['action']
        if command['action'] != 'play_card':
            continue
        card = cards[command['args']['card_index']]
        if card['id'] not in DEFENDS | {'CARD.SURVIVOR'}:
            continue
        count = len(state['hand']) - 1 if card['id'] == 'CARD.SURVIVOR' else 0
        for ordinal in range(max(1, count)):
            alternatives.append({'id': f"{choice['id']}-discard-{ordinal}" if count else choice['id'],
                                 'first_action': command, 'card_id': card['id'],
                                 'discard_ordinal': ordinal if count else None,
                                 'expected_discard_count': count})
    return {'plans': [{'id': 'actual_end', 'first_action': action('end_turn'),
                       'discard_ordinal': None, 'expected_discard_count': 0}]
                     + alternatives[:limit],
            'alternative_count': len(alternatives), 'truncated': max(0, len(alternatives) - limit)}


def arithmetic(state, plating=False):
    started = time.perf_counter()
    incoming = sum(intent_damage(e) for e in state['enemies'])
    block = state['player']['block']
    end_block = sum(max(0, p['amount']) for p in (state.get('player_powers') or [])
                    if p.get('name') == 'Plating') if plating else 0
    loss = min(state['player']['hp'], max(0, incoming - block - end_block))
    useful = []
    for card in state['hand']:
        if card.get('can_play') and card['id'] in DEFENDS | {'CARD.SURVIVOR'}:
            after_loss = min(state['player']['hp'], max(0, incoming - block - end_block
                                                      - max(0, card.get('stats', {}).get('block', 0))))
            useful.append({'card_index': card['index'], 'predicted_hp_gain': loss - after_loss})
    gain = max((v['predicted_hp_gain'] for v in useful), default=0)
    return {'incoming': incoming, 'current_block': block, 'plating_block': end_block,
            'predicted_loss': loss, 'best_predicted_hp_gain': gain,
            'flags_missed_defense': gain > 0, 'cards': useful,
            'seconds': time.perf_counter() - started,
            'scope': 'Preview only; does not simulate discard, triggers or future turns.'}


def fresh_discard(state, plan):
    if (state.get('decision') != 'card_select' or state.get('min_select', 1) != 1
            or state.get('max_select', 1) != 1):
        raise ValueError('Unsupported Survivor selection boundary')
    choices = macro_candidates(state)
    ordinal = plan['discard_ordinal']
    if (len(choices) != plan['expected_discard_count'] or ordinal is None
            or not 0 <= ordinal < len(choices)):
        raise ValueError('Fresh discard shape differs from nominated hand')
    return choices[ordinal]['action']


def boundary(state, entry):
    status = terminal(state)
    if status:
        return status
    if (state.get('decision') == 'combat_play' and state.get('round') == entry['round'] + 1
            and state.get('context') == entry.get('context')):
        return 'next_player_turn'
    raise ValueError('Did not reach the next player turn or a real terminal boundary')


def outcome(state):
    player = state.get('player', {})
    return {'hp': player.get('hp'), 'block': player.get('block'), 'energy': state.get('energy'),
            'gold': player.get('gold'), 'potions': player.get('potions'),
            'round': state.get('round'), 'powers': state.get('player_powers', []),
            'enemies': state.get('enemies', []),
            'hand': [{k: c.get(k) for k in ('id', 'name', 'cost', 'stats', 'index')}
                     for c in state.get('hand', [])],
            'draw_pile_count': state.get('draw_pile_count'),
            'discard_pile_count': state.get('discard_pile_count')}


def probe(case, plan, prefix, manifest, timeout=60):
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid,
                  {**manifest, 'scope': 'offline_end_turn_comparison', 'case': case['id'], 'plan': plan})
    started = time.monotonic()
    deadline = started + timeout
    engine = None
    state = {}
    result = {'probe_id': uid, 'case': case['id'], 'plan': plan, 'entry_hash': case['entry_hash'],
              'status': 'error', 'actions': []}

    def send(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('End-turn probe budget exhausted')
        engine.timeout = min(30, remaining)
        return engine.send(command)

    def play(command):
        nonlocal state
        if len(result['actions']) >= 3:
            raise ValueError('Branch action cap exceeded')
        choices = combat_candidates(state) if state.get('decision') == 'combat_play' else macro_candidates(state)
        if command not in [c['action'] for c in choices]:
            raise ValueError('Probe action not freshly legal')
        trace.write('before', {'state': state, 'state_hash': digest(state)})
        trace.write('candidates', choices)
        trace.write('selected', command)
        state = send(command)
        result['actions'].append(command)
        trace.write('after', {'state': state, 'state_hash': digest(state)})

    try:
        if any(c.get('cmd') not in ('start_run', 'action') for c in prefix):
            raise ValueError('Noncanonical prefix command')
        engine = Headless(trace.directory, timeout=min(30, timeout))
        for command in prefix:
            state = send(command)
        if digest(state) != case['entry_hash']:
            raise ValueError('Probe entry mismatch')
        result['entry_verified'] = True
        trace.write('entry', {'state': state, 'state_hash': digest(state)})
        replay_seconds = time.monotonic() - started
        play(plan['first_action'])
        if plan['id'] != 'actual_end' and not terminal(state):
            if plan.get('card_id') == 'CARD.SURVIVOR':
                play(fresh_discard(state, plan))
            if state.get('decision') != 'combat_play' or state.get('round') != case['round']:
                raise ValueError('Unexpected turn change before planned end')
            play(action('end_turn'))
        result.update(status=boundary(state, case['state']), after_hash=digest(state),
                      outcome=outcome(state), replay_seconds=round(replay_seconds, 6))
        if plan['id'] == 'actual_end':
            result['original_after_matches'] = digest(state) == case['actual_after_hash']
            if not result['original_after_matches']:
                raise ValueError('Baseline diverges from original observed end-turn')
    except Exception as exc:
        result['status'] = 'error'
        result['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', result['error'])
    finally:
        if engine:
            engine.close()
    result['seconds'] = round(time.monotonic() - started, 6)
    wire = trace.directory / 'wire.jsonl'
    result['wire_sha256'] = hashlib.sha256(wire.read_bytes()).hexdigest() if wire.exists() else None
    trace.write('summary', result)
    result['trace_path'] = str(trace.path.relative_to(ROOT))
    result['trace_sha256'] = trace.close()
    return result
