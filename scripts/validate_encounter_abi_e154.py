#!/usr/bin/env python3
"""Frozen whole-history ABI regression; no altered game-state fixtures."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.checkpoints import file_hash, wire_pairs
from rsi.run_env import replay
from scripts.evaluate_battle_search_e120 import manifest, write, audit


def check(v, collection, output):
    start = time.monotonic()
    old = json.loads((ROOT/'experiments/E153/collection-v1.json').read_text())
    new = json.loads(collection.read_text())
    if [r['seed'] for r in old['records']] != [r['seed'] for r in new['records']]:
        raise ValueError('Changed fixed cohort')
    rows = []
    for a, b in zip(old['records'], new['records']):
        ap = wire_pairs((ROOT/a['trace_path']).with_name('wire.jsonl'))
        bp = wire_pairs((ROOT/b['trace_path']).with_name('wire.jsonl'))
        n = next((i for i, (x, y) in enumerate(zip(ap, bp)) if x != y), min(len(ap), len(bp)))
        row = dict(case=a['case'], old_status=a['status'], new_status=b['status'], exact_prefix_pairs=n,
                   old_pairs=len(ap), new_pairs=len(bp), full_match=ap == bp)
        if a['case'] == 'train-A0-011':
            row['pass'] = n == len(ap)-1 and ap[n][0] == bp[n][0] and bp[n][1].get('decision') == 'card_reward'
            row['after_failed_action'] = {k: bp[n][1].get(k) for k in ('decision', 'gold_earned', 'context')}
        elif a['case'] == 'dev-A0-002':
            before, after = ap[n][1], bp[n][1]
            row['first_difference_context'] = after.get('context')
            row['old_enemies'] = [{k:e.get(k) for k in ('id','name','hp','powers')} for e in before.get('enemies', [])]
            row['new_enemies'] = [{k:e.get(k) for k in ('id','name','hp','powers')} for e in after.get('enemies', [])]
            crusher = next((e for e in after.get('enemies', []) if e.get('name') == 'Crusher'), {})
            names = {e.get('name') for e in crusher.get('powers', [])}
            row['pass'] = (ap[n][0] == bp[n][0] and after.get('decision') == 'combat_play' and
                after.get('context', {}).get('room_type') == 'Boss' and
                {'Back Attack', 'Crab Rage'} <= names and before.get('decision') == 'card_reward' and
                before.get('gold_earned') == 100 and before.get('context') == after.get('context'))
            row['old_decision'] = before.get('decision')
            row['new_decision'] = after.get('decision')
        else:
            row['pass'] = row['full_match'] and a['status'] == b['status']
        if a['status'] == 'error' and b['status'] in ('victory', 'defeat'):
            row['verification'] = replay(b, v, seconds=180)
            row['pass'] &= row['verification']['status'] == 'match'
        rows.append(row)
    same_game = all(v[k] == old['manifest'][k] for k in ('headless_game_sha256','game_dll_sha256'))
    out = dict(manifest=v, collection_sha256=file_hash(collection), checks=rows,
               proprietary_game_unchanged=same_game, audit=audit({'old':old,'new':new,'checks':rows}), seconds=time.monotonic()-start)
    out['pass'] = new['execution_pass'] and same_game and out['audit']['pass'] and all(r['pass'] for r in rows)
    write(output, out)
    print(json.dumps({k:out[k] for k in ('pass','proprietary_game_unchanged','audit','seconds')}))
    for row in rows:
        if not row['full_match']:
            print(json.dumps(row))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--collection',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.output).exists():raise ValueError('Preserve old evidence')
    check({**manifest(),'experiment':'E154'},Path(a.collection),Path(a.output))
