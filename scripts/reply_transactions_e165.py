#!/usr/bin/env python3
"""Materialize explicit fresh Astra answers, never choose automatically or commit."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsi.campaign_teacher import validate
from rsi.macro_transaction import owned_rules

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('answers',type=Path);a=p.parse_args()
    for case,answer in json.loads(a.answers.read_text()).items():
        req=json.loads((ROOT/'artifacts/runs/e165-pending'/f'{case}.json').read_text())
        if answer['seq']!=req['seq']:raise ValueError('Stale reply')
        packet={k:req[k] for k in ('case','run_id','seq','state_hash')}
        packet.update(choice_id=answer['choice'],campaign_plan=answer['plan'],
            potion_reservations=answer.get('reservations',owned_rules(req['state'],req['potion_reservations'])),
            acquire_reservation=answer.get('acquire'),transaction_steps=answer.get('steps',[]))
        if req.get('selection_contract'):packet['selected_indices']=answer['indices']
        validate(packet,req);target=ROOT/req['response_path']
        if target.exists():raise ValueError('Never overwrite teacher packet')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        print(str(target.relative_to(ROOT)))
