"""Supplement canonical trial audit with exact turn-plan provenance and expiry."""
import json
import subprocess
from rsi.engine import ROOT
from rsi.trace import digest
from rsi.turn_advisor import validate_packet


def main():
    d=ROOT/'experiments/E102';report=json.loads((d/'result.json').read_text());base=json.loads((d/'audit.json').read_text());audits=[]
    for r in report['results']:
        rows=[json.loads(l) for l in (ROOT/r['trace_path']).read_text().splitlines()]
        checks={'state_bound':True,'turn_bound':True,'committed':True,'one_per_turn':True,'advisory_only':True,'applied':True}
        current=None;request=None;packet=None;commit=None;rounds=[];last_round=None;applications=0
        for row in rows:
            k,v=row['kind'],row['data']
            if k=='before':
                current=v['state']
                if current.get('decision')=='combat_play':last_round=current['round']
            elif k=='turn_advice_request':
                request=v;checks['state_bound'] &= v['state_hash']==digest(current) and v['run_id']==r['run_id']
                checks['turn_bound'] &= v['round']==last_round
            elif k=='turn_advice_response':
                packet=v['packet'];commit=v['commit'];rounds.append(packet['round']);validate_packet(packet,request)
                path=f"experiments/E102/teacher/{r['run_id']}/{packet['round']:03}.json"
                checks['committed'] &= json.loads(subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT))==packet
            elif k=='turn_plan_applied':
                applications+=1;checks['state_bound'] &= v['state_hash']==digest(current)
                checks['turn_bound'] &= v['round']==last_round==packet['round'] and v['commit']==commit
            elif k=='model_request':
                plan=v['state'].get('astra_turn_plan')
                if r['turn_advice']:
                    checks['applied'] &= bool(plan) and plan['round']==last_round and plan['goal']==packet['goal'] and plan['guidance']==packet['guidance']
                else:checks['applied'] &= plan is None
        checks['one_per_turn']=len(rounds)==len(set(rounds))==r['expert_packets']
        checks['advisory_only']=r['expert_packets']<=30 and (applications==r['model_calls'] if r['turn_advice'] else applications==0)
        audits.append({'run_id':r['run_id'],'case':r['case'],'arm':r['arm'],'rounds':rounds,'checks':checks,'passed':all(checks.values())})
    out={'canonical_audit_passed':base['all_passed'],'turn_audits':audits,'all_passed':base['all_passed'] and all(a['passed'] for a in audits)}
    (d/'turn-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
