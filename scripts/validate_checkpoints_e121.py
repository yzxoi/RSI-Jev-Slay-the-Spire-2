#!/usr/bin/env python3
"""Checkpoint parity gates; outputs are immutable and every raw trace is retained."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsi.checkpoints import preflight_case
from rsi.trace import digest
from scripts.evaluate_battle_search_e120 import audit, frozen_bank, manifest, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('preflight',))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Do not overwrite earlier evidence')
    version = {**manifest(), 'experiment': 'E121'}
    bank = frozen_bank(ROOT / 'experiments/E120/fixtures.json')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda f: preflight_case(f, version), bank['fixtures']))
    report = {'manifest': version, 'source_bank_hash': digest(bank), 'results': results,
              'seconds': time.monotonic() - started,
              'summary': dict(Counter(r['status'] for r in results))}
    report['audit'] = audit(report)
    write(output, report)
    for r in results:
        print(json.dumps(r, ensure_ascii=False), flush=True)
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
