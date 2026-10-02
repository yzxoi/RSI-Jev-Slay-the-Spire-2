#!/usr/bin/env python3
"""Exact old-state compatibility plus real Rolling Boulder mechanics."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from rsi.battle_search import baseline_choice,compact
from rsi.checkpoints import file_hash,wire_pairs
from rsi.ppo_env import episode
from rsi.trace import digest
from rsi.training_bank import matched
from scripts.evaluate_battle_search_e120 import audit,manifest,write


def frozen_case(v,output):
    start=time.monotonic()
    bank_path=ROOT/'experiments/E133/fixtures-v1.json'
    certificate_path=ROOT/'experiments/E133/certificate-train-v1.json'
    bank=json.loads(bank_path.read_text())
    source=json.loads(certificate_path.read_text())
    f=next(f for f in bank['fixtures'] if f['case']=='train-150-b8')
    failed=next(r for r in source['records'] if r['case']==f['case'])['A']
    if not audit({'f':f,'failed':failed})['pass']:
        raise ValueError('Original failure evidence changed')
    pairs=wire_pairs((ROOT/failed['trace_path']).with_name('wire.jsonl'))
    n=len(f['prefix'])
    if [c for c,_ in pairs[:n]]!=f['prefix'] or failed['steps']!=4:
        raise ValueError('Frozen failure history changed')
    state=pairs[n-1][1]
    steps=[]
    for command,after in pairs[n:n+4]:
        steps.append(dict(before=digest(state),action=command,after=digest(after)))
        state=after
    if digest(steps)!=failed['transition_hash']:
        raise ValueError('Old successful transitions changed')
    old_failed_command=pairs[n+4][0]
    def policy(state,choices,previous,plan):
        i=len(plan)
        if i<4:
            if digest(state)!=steps[i]['before']:
                raise ValueError('Pre-error state changed')
            choice=next(c for c in choices if c['action']==steps[i]['action'])
        elif i==4:
            if digest(state)!=steps[-1]['after']:
                raise ValueError('Previously failing turn-start state changed')
            choice=next(c for c in choices if c['action']==old_failed_command)
        else:
            choice=baseline_choice(state,previous)
        return choice,{'source':'frozen_failure_then_unchanged_planner'}
    current,_=episode(f,v,'rolling_boulder_regression',policy=policy)
    report=dict(manifest=v,source_bank_sha256=file_hash(bank_path),source_certificate_sha256=file_hash(certificate_path),
                case=f['case'],original_failure=failed,primary=compact(current),replays=[])
    wire=wire_pairs((ROOT/current['trace_path']).with_name('wire.jsonl'))
    if len(wire)>n+4 and wire[n+4][1].get('decision')=='combat_play':
        before,after=wire[n+3][1],wire[n+4][1]
        def power(s):return next(p['amount'] for p in s['player_powers'] if p['name']=='Rolling Boulder')
        report['mechanic']=dict(before_round=before['round'],after_round=after['round'],
            before_enemy_hp=before['enemies'][0]['hp'],after_enemy_hp=after['enemies'][0]['hp'],
            before_power=power(before),after_power=power(after))
        report['mechanic_pass']=(report['mechanic']==dict(before_round=1,after_round=2,before_enemy_hp=83,
            after_enemy_hp=78,before_power=5,after_power=10))
    else:
        report['mechanic_pass']=False
    report['pre_error_match']=current['plan'][:4]==steps
    if current['status'] in ('clear','defeat') and report['mechanic_pass'] and report['pre_error_match']:
        for repeat in range(3):
            replay,_=episode(f,v,f'rolling_boulder_replay:{repeat}',expected=current['plan'])
            replay['match']=matched(current,replay)
            report['replays'].append(compact(replay))
    report['passed']=(report['mechanic_pass'] and report['pre_error_match'] and len(report['replays'])==3
                      and all(r['match'] for r in report['replays']))
    report['audit']=audit(report)
    report['passed'] &= report['audit']['pass']
    report['seconds']=time.monotonic()-start
    write(output,report)
    print(json.dumps({k:report[k] for k in ('passed','mechanic_pass','pre_error_match','audit','seconds')}
                     | {'primary_status':current['status'],'error':current.get('error'),'mechanic':report.get('mechanic')}),flush=True)


def compare_bank(v,new_path,output):
    old_path=ROOT/'experiments/E133/fixtures-v1.json'
    old=json.loads(old_path.read_text())
    new=json.loads(Path(new_path).read_text())
    if old['configs']!=new['configs']:
        raise ValueError('Changed preparation configs')
    checks=[]
    for a,b in zip(old['seeds'],new['seeds']):
        ap=wire_pairs((ROOT/a['trace_path']).with_name('wire.jsonl'))
        bp=wire_pairs((ROOT/b['trace_path']).with_name('wire.jsonl'))
        fields=('case','prefix_hash','entry_hash','hp','room_type','enemies','ordinal')
        checks.append(dict(case=a['case'],status_match=a['status']==b['status'],
                           full_command_state_sequence_match=ap==bp,
                           entry_match=[{k:f[k] for k in fields} for f in a['entries']]==[
                               {k:f[k] for k in fields} for f in b['entries']],commands=len(ap)))
    before=json.loads((ROOT/'experiments/E135/environment-before.json').read_text())
    same_game=all(v[k]==before[k] for k in ('headless_game_sha256','game_dll_sha256'))
    report=dict(manifest=v,old_engine=before,new_engine=v,
                old_bank=dict(path=str(old_path.relative_to(ROOT)),sha256=file_hash(old_path)),
                new_bank=dict(path=str(new_path),sha256=file_hash(new_path)),checks=checks,
                proprietary_game_dlls_unchanged=same_game,
                audit=audit({'old':old,'new':new}))
    report['passed']=(new['passed'] and len(checks)==264 and same_game and report['audit']['pass']
                      and all(r['status_match'] and r['entry_match'] and r['full_command_state_sequence_match'] for r in checks))
    write(output,report)
    print(json.dumps({'passed':report['passed'],'seeds':len(checks),'commands':sum(r['commands'] for r in checks),
                      'entries':len(new['fixtures']),'same_game_dlls':same_game,'audit':report['audit']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('case','compare-bank'))
    p.add_argument('--new-bank');p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.output).exists():raise ValueError('Preserve old evidence')
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    v={**manifest(),'experiment':'E135','scope':'ABI compatibility; original TestMode damage logic'}
    if a.phase=='case':frozen_case(v,a.output)
    else:compare_bank(v,a.new_bank,a.output)
