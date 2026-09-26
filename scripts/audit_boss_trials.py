"""Read-only reconciliation for experimental canonical Boss traces and branch proofs."""
import argparse
from collections import Counter
import hashlib
import json
from rsi.engine import ROOT
from rsi.potion_contract import PotionContract
from rsi.teacher import terminal
from rsi.trace import digest


def file_hash(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def audit_proof(proof, prefix=None):
    p=ROOT/proof['trace_path'];rows=[json.loads(l) for l in p.read_text().splitlines()]
    wire=p.with_name('wire.jsonl');ws=[json.loads(l) for l in wire.read_text().splitlines()]
    commands=[r['data'] for r in ws if r['kind']=='command'];states=[r['data'] for r in ws if r['kind']=='state' and r['data'].get('type')!='ready']
    entry=next(r['data']['state'] for r in rows if r['kind']=='entry');after=next(r['data']['state'] for r in rows if r['kind']=='after')
    checks={'hash':file_hash(p)==proof['trace_sha256'] and file_hash(wire)==proof['wire_sha256'],
            'entry':digest(entry)==proof['entry_hash']==digest(states[-2]),
            'action':commands[-1]==proof['action'],'after':digest(after)==proof['after_hash']==digest(states[-1]),
            'real_boundary':bool(proof['certified'])==(terminal(after)=='boss_clear' and after['player']['hp']>0),
            'no_debug':all(c.get('cmd') in ('start_run','action') for c in commands),
            'prefix':prefix is None or commands[:-1]==prefix}
    return {'probe_id':proof['probe_id'],'checks':checks,'passed':all(checks.values())}


def audit_run(r,case):
    p=ROOT/r['trace_path'];rows=[json.loads(l) for l in p.read_text().splitlines()];wire=p.with_name('wire.jsonl')
    ws=[json.loads(l) for l in wire.read_text().splitlines()]
    cmds=[x['data'] for x in ws if x['kind']=='command'];states=[x['data'] for x in ws if x['kind']=='state' and x['data'].get('type')!='ready']
    entry=next(x['data']['state'] for x in rows if x['kind']=='entry');prefix=list(case['commands']);n=len(prefix)
    checks={'trace_hash':file_hash(p)==r['trace_sha256'],'wire_hash':file_hash(wire)==r['wire_sha256'],
            'entry':digest(entry)==case['entry_hash']==digest(states[n-1]),'prefix':cmds[:n]==prefix,
            'no_debug':all(c.get('cmd') in ('start_run','action') for c in cmds),'state_chain':True,'legal':True,
            'contracts':True,'certificates':True,'terminal_scope':True}
    pc=PotionContract(entry,r['contract']) if r.get('contract') else None
    trans=[];state=entry;before=entry;choices=[];allowed=[];sel={};contract_expected=None;contract_ev={};proofs=[];sources=Counter()
    for row in rows:
        k,v=row['kind'],row['data']
        if k=='before':before=v['state'];checks['state_chain'] &= digest(before)==digest(state)==v['state_hash']
        elif k=='candidates':choices=v
        elif k=='allowed_candidates':allowed=v
        elif k=='lethal_check':proofs=v
        elif k=='resource_contract':
            contract_expected,expected_allowed,contract_ev=pc.prepare(before,choices)
            checks['contracts'] &= v==contract_ev
        elif k=='selected':
            sel=v;choice=v['choice'];sources[v['source']]+=1;checks['legal'] &= choice in choices
            if v['source']=='potion_contract':checks['contracts'] &= choice==contract_expected
            if v['source'] in ('jev','only_legal_choice'):checks['legal'] &= choice in allowed
            if v['source']=='certified_lethal':
                positive=next((x for x in proofs if x['certified']),None)
                checks['certificates'] &= bool(positive) and positive['action']==choice['action'] and positive['entry_hash']==digest(before)
                if positive:checks['certificates'] &= audit_proof(positive,prefix)['passed']
        elif k=='after':
            state=v['state'];idx=len(trans);choice=sel['choice']
            checks['state_chain'] &= digest(state)==v['state_hash'] and cmds[n+idx]==choice['action'] and states[n+idx]==state
            if sel['source']=='potion_contract':pc.accepted(contract_ev['rule_id'],before,state)
            if sel['source']=='certified_lethal':checks['certificates'] &= digest(state)==positive['after_hash'] and terminal(state)=='boss_clear'
            trans.append([digest(before),choice['action'],digest(state)]);prefix.append(choice['action'])
            if n+idx+1<len(cmds):checks['terminal_scope'] &= terminal(state) is None
    checks['terminal_scope'] &= terminal(state)==r['status']
    checks['trajectory']=digest(trans)==r['trajectory_sha256'] and digest(state)==r['final_state_hash']
    checks['counts']=len(trans)==r['steps']==len(cmds)-n and len(cmds)==len(states)
    checks['program_counts']=sources['potion_contract']==r['program_actions'] and sources['certified_lethal']==r.get('lethal_actions',0)
    checks['contracts'] &= (sorted(pc.done) if pc else [])==r.get('fulfilled',[])
    model_responses=[x['data']['response'] for x in rows if x['kind']=='model_response']
    checks['usage']=len(model_responses)+r['unknown_model_calls']==r['model_calls'] and abs(sum(x.get('usage',{}).get('cost',0) for x in model_responses)-r['model_cost_usd'])<1e-10
    checks['clean_tested_tree']=r['manifest']['tracked_dirty'] is False
    return {'run_id':r['run_id'],'case':r['case'],'arm':r['arm'],'repeat':r['repeat'],'checks':checks,'sources':dict(sources),'passed':all(checks.values())}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',required=True);a=ap.parse_args();exp=a.experiment.upper()
    report=json.loads((ROOT/f'artifacts/runs/{exp.lower()}-results.json').read_text())
    cases={c['id']:c for c in json.loads((ROOT/'experiments/E099/fixtures.json').read_text())['cases']}
    audits=[audit_run(r,cases[r['case']]) for r in report['results']]
    branches=[]
    mech=ROOT/f'artifacts/runs/{exp.lower()}-mechanics.json'
    if mech.exists():
        m=json.loads(mech.read_text());branches=[audit_proof(p) for p in m['results']]
        (ROOT/f'experiments/{exp}/mechanics.json').write_text(json.dumps(m,indent=2)+'\n')
    arms=sorted({r['arm'] for r in report['results']})
    report['summary']={arm:{'battles':sum(r['arm']==arm for r in report['results']),
           'clears':sum(r['arm']==arm and r['status']=='boss_clear' for r in report['results']),
           'model_calls':sum(r['model_calls'] for r in report['results'] if r['arm']==arm),
           'model_usd':sum(r['model_cost_usd'] for r in report['results'] if r['arm']==arm),
           'program_actions':sum(r['program_actions'] for r in report['results'] if r['arm']==arm),
           'lethal_actions':sum(r.get('lethal_actions',0) for r in report['results'] if r['arm']==arm)} for arm in arms}
    out={'experiment':exp,'canonical_runs':audits,'mechanic_branches':branches,'all_passed':all(r['passed'] for r in audits+branches)}
    d=ROOT/f'experiments/{exp}';(d/'result.json').write_text(json.dumps(report,indent=2)+'\n');(d/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'summary':report['summary'],'audit_passed':out['all_passed'],'session':report['session']},indent=2))
    if not out['all_passed']:print(json.dumps([r for r in audits+branches if not r['passed']],indent=2))

if __name__=='__main__':main()
