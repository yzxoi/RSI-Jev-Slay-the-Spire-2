#!/usr/bin/env python3
"""Audit all E118 phases and compose results without reissuing model requests."""
import argparse,json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'scripts')]
import benchmark_shallow_e118 as b
import resume_shallow_e118 as r

def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,default=root/'artifacts/runs/e118-final')
    parser.add_argument('--public-output',type=Path,default=root/'experiments/E118/final')
    args=parser.parse_args()
    bank=json.loads((root/'experiments/E118/fixtures.json').read_text())
    base=root/'artifacts/runs/e118-pilot-v2'
    s3=root/'artifacts/runs/e118-supplement-v3';s4=root/'artifacts/runs/e118-supplement-v4'
    source3=root/'artifacts/runs/e118-combined-v3'
    a2=b.audit(bank,base)
    a3={c:r.audit_config(c,bank,base,s3) for c in ['deepseek_low','qwen_low']}
    a4={c:r.audit_config(c,bank,source3,s4) for c in ['deepseek_low','qwen_low','kimi_low']}
    out=args.output
    shutil.copytree(base,out)
    for s in [s3,s4]:
     for c in json.loads((s/'manifest.json').read_text())['configs']:
      shutil.copytree(s/c,out/c,dirs_exist_ok=True)
    meta=json.loads((base/'manifest.json').read_text())
    meta.update(aggregation_only=True,source_phases=['e118-pilot-v1','e118-pilot-v2','e118-supplement-v3','e118-supplement-v4'],
        phase_tested_shas={n:json.loads((root/'artifacts/runs'/n/'manifest.json').read_text())['tested_sha'] for n in ['e118-pilot-v1','e118-pilot-v2','e118-supplement-v3','e118-supplement-v4']})
    for c in ['deepseek_low','qwen_low','kimi_low']:
     meta['config_tested_shas'][c]=[meta['config_tested_shas'][c]]+([json.loads((s3/'manifest.json').read_text())['tested_sha']] if c!='kimi_low' else [])+[json.loads((s4/'manifest.json').read_text())['tested_sha']]
    b.write_json(out/'manifest.json',meta)
    summary=b.summarize(bank,out);b.write_json(out/'summary.json',summary)
    rows=[];caps={};jev=json.loads((out/'jev/rows.json').read_text());j={(x['item_id'],x['task']):x for x in jev}
    for c in meta['configurations']:
     xs=json.loads((out/c/'rows.json').read_text());rows+=xs
     main=[x for x in xs if x['task']!='readout'];valid=[x for x in main if x['valid']]
     sm=summary['configurations'][c]
     caps[c]={'correct_main':sum(x['correct'] for x in main),'valid_main':len(valid),'planned_main':96,
      'matched_jev_correct_main':sum(j[x['item_id'],x['task']]['correct'] for x in valid),
      'attempted_all':sum(x.get('attempted',False) for x in xs),'valid_all':sum(x['valid'] for x in xs),
      'eligible_full_range':sm['reliable'],'prefix_if_eligible':sm['empirical_contiguous_passing_prefix'] if sm['reliable'] else None,
      'readout':sm['readout'],'cost':sm['usage_totals']['cost'],'unknown_reservation':sm['manifest']['ledger']['unknown_reserved'],
      'errors':dict(b.collections.Counter(x['error'] for x in xs if x.get('attempted') and not x['valid'])),
      'known_correct_fraction_of_full_bank':sum(x['correct'] for x in main)/96,
      'missing_answer_bounds_not_confidence_interval':[sum(x['correct'] for x in main)/96,(sum(x['correct'] for x in main)+96-len(valid))/96],
      'root_correct_by_h':[sm['by_horizon'][str(h)]['choice']['correct'] for h in [1,2,4,8]],
      'root_valid_by_h':[sm['by_horizon'][str(h)]['choice']['valid'] for h in [1,2,4,8]],
      'prediction_pairs_correct_by_h':[sm['by_horizon'][str(h)]['prediction_both_mappings_correct'] for h in [1,2,4,8]],
      'semantic_prediction_confusion':dict(b.collections.Counter(('truth_yes' if x['semantic_truth'] else 'truth_no')+('_answer_yes' if x['semantic_yes'] else '_answer_no') for x in valid if x['task'].startswith('predict')))}
    physical=a2['request_response_pairs'];physical=sum(physical.values())+sum(x['new_pairs'] for x in a3.values())+sum(x['new_pairs'] for x in a4.values())
    assert physical==summary['attempted_calls']
    assert summary['total_reported_cost_usd']+summary['total_unknown_reservation_usd']<=3
    b.write_json(out/'audit.json',{'passed':True,'base_phase':a2,'continuation_3':a3,'continuation_4':a4,'unique_physical_requests':physical,'failed_cells_retried':0,'all_fixture_hashes_match':True})
    b.write_json(out/'capability-summary.json',caps)
    p=args.public_output;p.mkdir(parents=True,exist_ok=True)
    for n in ['manifest.json','summary.json','audit.json','capability-summary.json']:shutil.copyfile(out/n,p/n)
    (p/'rows.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
    p4=args.public_output.parent/'iteration-4';p4.mkdir(parents=True,exist_ok=True)
    for n in ['manifest.json','audit.json']:
     if (s4/n).exists():shutil.copyfile(s4/n,p4/n)
    for c in ['deepseek_low','qwen_low','kimi_low']:
     (p4/(c+'-manifest.json')).write_text(json.dumps(json.loads((s4/c/'manifest.json').read_text()),separators=(',',':'))+'\n')
    print(json.dumps({'configurations':caps,'totals':{k:summary[k] for k in ['attempted_calls','valid_calls','total_reported_cost_usd','total_unknown_reservation_usd']}},indent=2))


if __name__=="__main__": main()
