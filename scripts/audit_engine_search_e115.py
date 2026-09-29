"""Verify saved evidence independently of the online chooser's counters."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from rsi.engine import ROOT
from rsi.engine_search import EMPTY_PREFIX, extend_prefix, position
from rsi.trace import digest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_trace(result, expected_sha):
    path = ROOT / result['trace_path']
    assert sha(path) == result['trace_sha256'], path
    assert sha(path.parent / 'wire.jsonl') == result['wire_sha256'], path
    assert sha(path.parent / 'engine.stderr.log') == result['stderr_sha256'], path
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    wire = [json.loads(line) for line in (path.parent / 'wire.jsonl').read_text().splitlines()]
    manifest = rows[0]['data']
    assert manifest['code_commit'] == expected_sha and not manifest['tracked_dirty']
    commands = [r['data'] for r in wire if r['kind'] == 'command']
    assert commands[0]['cmd'] == 'start_run'
    assert all(c['cmd'] == 'action' for c in commands[1:])
    replay_count = result.get('replay_commands', 1)
    key = EMPTY_PREFIX
    for command in commands[:replay_count]:
        key = extend_prefix(key, command)
    speculative = manifest['scope'] == 'speculative_battle'
    if speculative and result['entry_verified']:
        entry = next(r['data'] for r in rows if r['kind'] == 'entry')
        assert key == manifest['prefix_hash'] == entry['prefix_hash']
        assert digest(entry['state']) == manifest['entry_hash'] == result['entry_hash']
    steps = []
    before = choice = candidates = evidence = after_state = None
    for row in rows[1:]:
        kind, data = row['kind'], row['data']
        if kind == 'before':
            before = data
            assert digest(before['state']) == before['state_hash']
            assert before['prefix_hash'] == key
            candidates = choice = evidence = None
        elif kind == 'candidates':
            candidates = data
        elif kind == 'decision_source':
            evidence = data.get('evidence')
        elif kind == 'selected':
            choice = data
            assert before is not None and candidates is not None
            assert choice['action'] in [c['action'] for c in candidates]
        elif kind == 'after':
            assert before and choice
            assert digest(data['state']) == data['state_hash']
            assert commands[replay_count + len(steps)] == choice['action']
            step = dict(prefix_hash=key, before=before['state_hash'],
                        action=choice['action'], after=data['state_hash'], evidence=evidence)
            steps.append(step)
            key = extend_prefix(key, choice['action'])
            after_state = data['state']
    # A failed send can have one extra command with no settled response. Normal
    # canonical and complete speculative outcomes must have exact equality.
    if result['status'] in ('act1_clear', 'defeat', 'clear'):
        assert len(commands) == replay_count + len(steps)
        assert len(steps) == result['steps']
    if not speculative and result['status'] == 'act1_clear':
        assert position(after_state)[0] > 1 and after_state['player']['hp'] > 0
    if not speculative and result['status'] == 'defeat':
        assert after_state['decision'] == 'game_over' and not after_state.get('victory')
    return manifest, commands, steps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite previous audit evidence')
    counts = Counter()
    sources = []
    for name in args.reports:
        report_path = Path(name)
        report = json.loads(report_path.read_text())
        sources.append({'path': name, 'sha256': sha(report_path)})
        expected_sha = report['manifest']['code_commit']
        for run in report['results']:
            branch_steps = {}
            branch_prefixes = []
            for branch in run.get('search', {}).get('probes', []):
                manifest, commands, steps = check_trace(branch, expected_sha)
                counts['speculative_traces'] += 1
                counts['speculative_transitions'] += len(steps)
                if branch['entry_verified']:
                    branch_prefixes.append(commands[:branch['replay_commands']])
                    counts['verified_entries'] += 1
                for step in steps:
                    branch_steps[(branch['run_id'], step['prefix_hash'], step['before'],
                                  digest(step['action']), step['after'])] = manifest['policy']
            _, commands, steps = check_trace(run, expected_sha)
            counts['canonical_traces'] += 1
            counts['canonical_transitions'] += len(steps)
            for prefix in branch_prefixes:
                assert prefix == commands[:len(prefix)], 'Branch did not restore actual canonical history'
            for step in steps:
                proof = step['evidence']
                if proof:
                    evidence_key = (proof['source_trace'], step['prefix_hash'], step['before'],
                                    digest(step['action']), step['after'])
                    assert branch_steps[evidence_key] == proof['mode']
                    assert step['before'] == proof['before'] and step['after'] == proof['after']
                    counts['canonical_predictions_verified'] += 1
    result = dict(passed=True, reports=sources, counts=dict(counts),
                  scope='Trace integrity, actual-prefix provenance, candidate membership and transition evidence; not simulator correctness or playing strength.')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
