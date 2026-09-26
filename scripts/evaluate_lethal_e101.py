import argparse
import hashlib
import json
from pathlib import Path
from rsi.boss_trial import battle
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.lethal_certificate import nominate, probe
from rsi.policy import combat_candidates
from rsi.trace import digest,version_manifest

D=ROOT/'experiments/E101'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['mechanics','battles'],required=True);ap.add_argument('--source-root',type=Path);a=ap.parse_args()
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise ValueError('Commit before testing')
    cases={c['id']:c for c in json.loads((ROOT/'experiments/E099/fixtures.json').read_text())['cases']}
    if a.stage=='mechanics':
        results=[];states=0;abstained=0
        for source in json.loads((D/'inputs.json').read_text())['runs']:
            p=a.source_root/source['trace_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==source['trace_sha256']
            rows=[json.loads(l) for l in p.read_text().splitlines()];prefix=list(cases[source['case']]['commands']);seen=[]
            for row in rows:
                if row['kind']=='before':
                    state=row['data']['state'];h=digest(state);seen.append(h);states+=1
                    nominated=nominate(state,combat_candidates(state)) if state.get('decision')=='combat_play' else []
                    if not nominated:abstained+=1
                    for c in nominated:results.append(probe(state,c,prefix,manifest,source['run_id']))
                elif row['kind']=='selected':prefix.append(row['data']['choice']['action'])
            assert seen==source['before_hashes']
        out={'experiment':'E101','scope':'Offline counterfactual one-action mechanics, not new battles','manifest':manifest,'states':states,'abstained_states':abstained,'results':results}
        (ROOT/'artifacts/runs/e101-mechanics.json').write_text(json.dumps(out,indent=2)+'\n')
        print(json.dumps({'states':states,'abstentions':abstained,'nominations':len(results),'certified':sum(r['certified'] for r in results),'errors':[r for r in results if r['status']=='error']}))
    else:
        mechanical=json.loads((ROOT/'artifacts/runs/e101-mechanics.json').read_text())
        witness='5d88f1ad36aec0c5a98003bdcf00ecb467d7463661818211827ca406c35251be'
        assert any(r['entry_hash']==witness and r['certified'] for r in mechanical['results'])
        assert all(r['status']!='error' for r in mechanical['results'])
        session=Budget(2880,1.,conservative_failures=True);results=[]
        for repeat in range(3):
            for case in cases.values():
                for arm in (['baseline','lethal'] if repeat%2==0 else ['lethal','baseline']):
                    results.append(battle(case,arm,repeat,'E101',session,lethal=arm=='lethal'))
        out={'experiment':'E101','manifest':manifest,'results':results,'session':{'calls':session.calls,'reported_usd':session.spent-session.estimated_usd,'unknown_calls':session.uncertain_calls,'budgeted_usd':session.spent}}
        (ROOT/'artifacts/runs/e101-results.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
