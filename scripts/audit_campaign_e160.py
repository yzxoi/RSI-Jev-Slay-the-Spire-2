#!/usr/bin/env python3
"""Post-hoc read-only trace diagnosis and exact recorded-prefix replays; no new policy decisions."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.run_env import replay
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import audit


def main(source, output):
    if output.exists(): raise ValueError('Never overwrite evidence')
    evaluation=json.loads(source.read_text());records=evaluation['records'];start=time.monotonic()
    report={'scope':'Post-hoc descriptive audit; interrupted prefix replays are not terminal runs or new win samples',
            'source_sha256':file_hash(source),'audit_code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'original_gate_unchanged':evaluation['continuation_gate'],'requests':[],'treatment_prefix_replays':[]}
    for r in records:
        if r['arm']!='astra_campaign': continue
        events=[json.loads(line) for line in (ROOT/r['trace_path']).read_text().splitlines()]
        requests=[e['data'] for e in events if e['kind']=='campaign_request']
        phase=Counter(q['state']['decision'] for q in requests)
        forced_maps=sum(q['state']['decision']=='map_select' and len(q['state'].get('choices',[]))==1 for q in requests)
        report['requests'].append({'case':r['case'],'phases':dict(phase),'single_route_with_alternative_resource_action':forced_maps,
                                   'input_chars':r['expert_input_chars'],'packets':r['expert_packets']})
        result=replay(r,evaluation['manifest'],seconds=120)
        report['treatment_prefix_replays'].append(result)
        if r['case']=='A5-000':
            rounds=defaultdict(list);targets=Counter();juggernaut=[]
            for e in events:
                if e['kind']!='decision':continue
                d=e['data'];s=d['state'];c=s.get('context',{})
                if (c.get('act'),c.get('floor'),s['decision'])!=(2,11,'combat_play'):continue
                chosen=d['chosen'];a=chosen['action'];idx=a.get('args',{}).get('target_index')
                target=next((x['name'] for x in s['enemies'] if x['index']==idx),None)
                if a['action']=='play_card' and target:targets[target]+=1
                rounds[s['round']].append({'trace_seq':e['seq'],'hp':s['player']['hp'],'energy':s['energy'],
                    'choice':chosen['name'],'target':target,'leader_hp':next(x['hp'] for x in s['enemies'] if x['name']=='The Obscura')})
                if any(h['name']=='Juggernaut' and h.get('can_play') for h in s['hand']):
                    juggernaut.append({'trace_seq':e['seq'],'round':s['round'],'chosen':chosen['name']})
            report['obscura']={'case':r['case'],'act':2,'floor':11,'start_hp':83,'post_reward_hp':16,
                'attack_targets':dict(targets),'juggernaut_playable_but_other_chosen':juggernaut,
                'juggernaut_plays':sum(a['choice']=='Juggernaut' for actions in rounds.values() for a in actions),
                'rounds':dict(rounds),'causal_limit':'Observed execution mismatch; no alternative policy outcome or causal HP saving measured.'}
    report['prefix_raw_audit']=audit(report['treatment_prefix_replays'])
    report['seconds']=time.monotonic()-start
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'prefix_replays':[r['status'] for r in report['treatment_prefix_replays']],
                      'audit':report['prefix_raw_audit'],'seconds':report['seconds']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.source,a.output)
