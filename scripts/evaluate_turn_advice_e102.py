from concurrent.futures import ThreadPoolExecutor
import json
from rsi.boss_trial import battle
from rsi.engine import ROOT
from rsi.jev import Budget
from rsi.trace import version_manifest


def main():
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise ValueError('Commit before evaluation')
    for experiment in ['E100','E101']:
        audit=json.loads((ROOT/f'experiments/{experiment}/audit.json').read_text())
        if not audit['all_passed']:raise ValueError('Upstream safeguard audit failed')
    cases=json.loads((ROOT/'experiments/E099/fixtures.json').read_text())['cases']
    contracts=json.loads((ROOT/'experiments/E100/contracts.json').read_text());session=Budget(960,.8,conservative_failures=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(battle,c,arm,0,'E102',session,contract=contracts[c['id']],lethal=True,turn_advice=arm=='dynamic')
              for c in cases for arm in ['baseline','dynamic']]
        results=[j.result() for j in jobs]
    report={'experiment':'E102','manifest':manifest,'results':results,'session':{'calls':session.calls,'reported_usd':session.spent-session.estimated_usd,'unknown_calls':session.uncertain_calls,'budgeted_usd':session.spent}}
    (ROOT/'artifacts/runs/e102-results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
