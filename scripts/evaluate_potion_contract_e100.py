import json
from rsi.boss_trial import battle
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.trace import version_manifest


def main():
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise ValueError('Commit before evaluation')
    d=ROOT/'experiments/E100';cases=json.loads((ROOT/'experiments/E099/fixtures.json').read_text())['cases']
    contracts=json.loads((d/'contracts.json').read_text());session=Budget(2880,1.,conservative_failures=True);results=[]
    for repeat in range(3):
        for case in cases:
            for arm in (['baseline','contract'] if repeat%2==0 else ['contract','baseline']):
                results.append(battle(case,arm,repeat,'E100',session,contract=contracts[case['id']] if arm=='contract' else None))
    report={'experiment':'E100','manifest':manifest,'results':results,'session':{'calls':session.calls,'reported_usd':session.spent-session.estimated_usd,'unknown_calls':session.uncertain_calls,'budgeted_usd':session.spent}}
    (ROOT/'artifacts/runs/e100-results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
