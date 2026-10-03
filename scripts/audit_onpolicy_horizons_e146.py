#!/usr/bin/env python3
"""Read-only audit that changing the stop boundary did not change earlier play."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.checkpoints import wire_pairs
from rsi.trace import digest


def main(evaluation,output):
    report=json.loads(evaluation.read_text());pairs=[]
    for actor in report['checkpoints']:
        for asc in (0,5,10):
            for i in range(10):
                left=next(x for x in report['records'] if x['case']==f'six-{actor}-A{asc}-{i:02}')
                right=next(x for x in report['records'] if x['case']==f'act1-{actor}-A{asc}-{i:02}')
                x=wire_pairs((ROOT/left['trace_path']).with_name('wire.jsonl'))
                y=wire_pairs((ROOT/right['trace_path']).with_name('wire.jsonl'));n=min(len(x),len(y))
                pairs.append(dict(actor=actor,ascension=asc,seed=left['seed'],commands_compared=n,
                    matches=digest(x[:n])==digest(y[:n]),six_trace_sha256=left['trace_sha256'],act_trace_sha256=right['trace_sha256']))
    out=dict(scope='Post-hoc compatibility audit, no new game actions or strength claim',pairs=pairs,
             **{'pass':all(p['matches'] for p in pairs)},commands_compared=sum(p['commands_compared'] for p in pairs))
    output.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve prior audit')
    main(a.evaluation,a.output)
