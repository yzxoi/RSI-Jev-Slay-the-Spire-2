"""Audit the fixed native bridge states without claiming a game replay."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from rsi.event_guard import bound_bridge_reroll
from rsi.scenes import candidates


EXPECTED_TRACE_SHA256 = 'af5b26f4b86eb86ebfe322c274f65b681e1adca2046fb8abbb2deff7ef3146a3'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    trace_bytes = args.trace.read_bytes()
    digest = hashlib.sha256(trace_bytes).hexdigest()
    if digest != EXPECTED_TRACE_SHA256:
        raise ValueError('Fixed E051 trace SHA-256 mismatch')
    rows = []
    for line in trace_bytes.splitlines():
        record = json.loads(line)
        if record['kind'] != 'before':
            continue
        raw = record['data']['state']
        if (raw.get('event') or {}).get('event_id') != 'SLIPPERY_BRIDGE':
            continue
        offered = candidates(raw)
        kept, report = bound_bridge_reroll(raw, offered)
        reroll = next((choice for choice in offered
                       if '.options.HOLD_ON_' in (choice.get('details') or {}).get('text_key', '')), None)
        exit_choice = next((choice for choice in offered
                            if '.options.OVERCOME' in (choice.get('details') or {}).get('text_key', '')), None)
        if reroll is None or exit_choice is None:
            continue
        rows.append({
            'hp': raw['run']['current_hp'],
            'reroll_key': reroll['details']['text_key'],
            'reroll_allowed': reroll in kept,
            'exit_allowed': exit_choice in kept,
            'guard_reason': report['reason'],
        })
    result = {
        'tested_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'input_trace_sha256': digest,
        'states': rows,
        'initial_reroll_preserved': bool(rows and rows[0]['reroll_allowed']),
        'later_rerolls_excluded': sum(not row['reroll_allowed'] for row in rows[1:]),
        'exit_available_all_states': all(row['exit_allowed'] for row in rows),
        'scope': 'retrospective_candidate_filter_only',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'states'}))


if __name__ == '__main__':
    main()
