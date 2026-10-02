#!/usr/bin/env python3
"""Read-only E133 accounting, paired difficulty results and on-policy diagnostics."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.checkpoints import file_hash
from scripts.evaluate_battle_search_e120 import audit,write
from scripts.retrain_ppo_e133 import compare


def main(output):
    paths={k:ROOT/p for k,p in dict(
        bank='experiments/E133/fixtures-v2.json',
        failed_training='experiments/E133/training-v1.json',
        training='experiments/E133/training-v2.json',test='experiments/E133/test-v1.json',
        train_certificate='experiments/E134/recovery-train-v2.json',
        test_certificate='experiments/E134/recovery-test-v1.json').items()}
    reports={k:json.loads(p.read_text()) for k,p in paths.items()}
    train,test=reports['training'],reports['test']
    fixtures={f['case']:f for f in reports['bank']['fixtures']}
    result=dict(sources={k:dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p)) for k,p in paths.items()},
                models=[],arms={},by_difficulty_comparisons={},
                independent_test_seeds=48,test_panel_entries=96,
                execution_pass=test['execution_pass'],practical_improvement_pass=test['practical_improvement_pass'],
                longer_training_pass=test['longer_training_pass'])
    for row in train['learners']:
        for cp in row['checkpoints']:
            if file_hash(ROOT/cp['path'])!=cp['sha256']:raise ValueError('Checkpoint changed')
        old=next(r for r in reports['failed_training']['learners'] if r['learner']==row['learner'])
        rejected=[u for u in old['updates'] if 'optimization' not in u]
        result['models'].append(dict(learner=row['learner'],parameters=row['parameters'],
            effective_episodes=sum(len(u['episodes']) for u in row['updates']),
            optimized_transitions=sum(u['optimization']['transitions'] for u in row['updates']),
            rejected_batch_attempts=sum(len(u['episodes']) for u in rejected),
            reset_retry_attempts=sum(len(e.get('reset_retry_attempts',[])) for u in row['updates'] for e in u['episodes']),
            optimizer_seconds=sum(u['optimization_seconds'] for u in row['updates']),
            work_seconds=row['work_seconds'],training_validation_seconds=row['seconds'],
            short_selected=row['short_selected'],long_selected=row['long_selected'],
            validation_curve=[dict(update=v['update'],passed=v['passed'],panels=v['panels'],
                                   by_difficulty=v['by_difficulty']) for v in row['validations']]))
        name=f"long-{row['learner']}"
        for control in (f"E127-{row['learner']}",f"short-{row['learner']}",'planner'):
            result['by_difficulty_comparisons'][name+'_vs_'+control]={
                f'{panel}:A{asc}':compare(test['arms'][name],test['arms'][control],panel,asc)
                for panel in ('early','challenging') for asc in (0,5,10)}
    for name,arm in test['arms'].items():
        panels={}
        for panel in ('early','challenging'):
            records=[r for r in arm['records'] if r['panel']==panel]
            reference=[r for r in test['arms']['planner']['records'] if r['panel']==panel]
            if [r['case'] for r in records]!=[r['case'] for r in reference]:raise ValueError('Unpaired panel')
            calibration=[r['value_calibration'] for r in records if 'value_calibration' in r]
            disagreements=[]
            for r,baseline in zip(records,reference):
                if r['status']!=baseline['status']:
                    f=fixtures[r['case']]
                    disagreements.append(dict(case=r['case'],ascension=f['ascension'],entry_hp=f['hp'],
                        enemies=f['enemies'],arm_status=r['status'],planner_status=baseline['status'],
                        trace_path=r['trace_path'],trace_sha256=r['trace_sha256'],
                        **{k:r[k] for k in ('wire.jsonl_sha256','engine.stderr.log_sha256')},
                        value_calibration=r.get('value_calibration')))
            panels[panel]=dict(summary=arm['panels'][panel],versus_planner=compare(arm,test['arms']['planner'],panel),
                on_policy_value_mse=(sum(c['n']*c['mse'] for c in calibration)/sum(c['n'] for c in calibration)
                                     if calibration else None),outcome_disagreements=disagreements)
        result['arms'][name]=dict(passed=arm['passed'],alias_of=arm.get('alias_of'),panels=panels,
                                  by_difficulty=arm['by_difficulty'])
    for key in ('effective_episodes','optimized_transitions','rejected_batch_attempts','reset_retry_attempts',
                'optimizer_seconds','work_seconds','training_validation_seconds'):
        result['total_'+key]=sum(r[key] for r in result['models'])
    result['selected_policy_replays']=sum(r.get('verification_match',False)
        for k,a in test['arms'].items() if k.startswith(('short-','long-')) and not a.get('alias_of') for r in a['records'])
    result['audit']=audit(reports)
    result['notes']=[
        '48 independent test seeds shared by all arms; two within-seed panels and two learners are correlated.',
        'Initial failed batches and their work cost are retained; rejected attempts are not optimized episodes.',
        'HP-equivalent assigns legitimate defeats zero; incomplete panels are unscored.',
        'Value MSE is against each greedy policy own terminal return; paths differ, so this is not paired-state causal evidence.',
        'Models consume planner-prepared Ironclad Act1 battle entries, not learned route/reward or full-run policies.',
        'Three difficulty strata are A0/A5/A10, sixteen independent held-out seeds each.',
        'No external model API calls; assistant research/development cost is not included.']
    write(output,result)
    print(json.dumps({k:v for k,v in result.items() if k.startswith('total_') or k in (
        'execution_pass','practical_improvement_pass','longer_training_pass','selected_policy_replays','audit')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.output).exists():raise ValueError('Preserve previous analysis')
    main(Path(a.output))
