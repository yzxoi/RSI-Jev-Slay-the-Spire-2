#!/usr/bin/env python3
"""Materialize explicit Astra choices; never generates a choice or commits it."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.campaign_teacher import validate


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('answers',type=Path);a=p.parse_args()
    for case,answer in json.loads(a.answers.read_text()).items():
        request=json.loads((ROOT/'artifacts/runs/e160-pending'/f'{case}.json').read_text())
        if request['seq']!=answer['seq']:raise ValueError('Request advanced; reread before answering')
        packet={k:request[k] for k in ('case','run_id','seq','state_hash')}
        current_ids={x.get('id') for x in request['state']['player'].get('potions',[])}
        packet.update(choice_id=answer['choice'],campaign_plan=answer['plan'],
            potion_reservations=answer.get('reservations',[r for r in request['potion_reservations'] if r['potion_id'] in current_ids]))
        validate(packet,request)
        target=ROOT/request['response_path']
        if target.exists():raise ValueError('Never replace an expert response')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        print(str(target.relative_to(ROOT)))
