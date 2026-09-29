"""Read-only evidence validation and frozen role gates. Makes no API/game calls."""
from collections import Counter, defaultdict
import hashlib
import json
import math
import statistics
from pathlib import Path
from rsi.engine import ROOT
from rsi.trace import digest
from scripts.evaluate_deciders_e113 import ARMS, paired, summarize

D=ROOT/'experiments/E113'


def percentile(values,p):
    return sorted(values)[math.ceil(len(values)*p)-1] if values else None


def main():
    report=json.loads((D/'results.json').read_text());fixtures=json.loads((D/'fixtures.json').read_text())
    results=report['results'];failures=[];metrics={};providers=defaultdict(Counter);over_deadline=[];pairs=[]
    expected={(c['id'],t,a) for c in fixtures['cases'] for t in ['combat','reward'] for a in ARMS}
    actual=[(r['case'],r['task'],r['arm']) for r in results]
    if len(actual)!=len(set(actual)) or set(actual)!=expected: failures.append('missing or duplicate cells')
    if hashlib.sha256((D/'fixtures.json').read_bytes()).hexdigest()!=report['fixtures_sha256']:failures.append('fixture hash')
    if summarize(results)!=report['summary']:failures.append('summary reproduction')
    for case in fixtures['cases']:
        source=case['source'];path=ROOT/source['trace_path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['trace_sha256']:failures.append('source trace hash '+case['id'])
        for task in ['combat','reward']:
            if case[task] and digest(case[task]['entry'])!=case[task]['entry_hash']:failures.append('fixture entry hash '+case['id'])
    trace_count=0;parity=0;observations=defaultdict(Counter);examples=[];by_character={}
    for arm in ARMS:
        selected=[r for r in results if r['arm']==arm];responses=[];requests=0;bad=0
        for result in selected:
            if not result.get('trace_path'):continue
            path=ROOT/result['trace_path'];raw=path.read_bytes();trace_count+=1
            if hashlib.sha256(raw).hexdigest()!=result['trace_sha256']:failures.append('trace hash '+result['case']+'/'+arm)
            for name,key in [('wire.jsonl','wire_sha256'),('engine.stderr.log','stderr_sha256')]:
                if hashlib.sha256((path.parent/name).read_bytes()).hexdigest()!=result[key]:failures.append(key+' '+result['case'])
            rows=list(map(json.loads,raw.splitlines()));before=None
            if rows[0]['data']['code_commit']!=report['manifest']['code_commit']:failures.append('wrong tested SHA')
            if result.get('entry_verified'):parity+=1
            for row in rows:
                if row['kind']=='model_request':requests+=1
                if row['kind']=='model_failure':bad+=1
                if row['kind']=='model_response':
                    responses.append(row['data'])
                    if arm=='deepseek':
                        q=row['data']['response'];finish=q['choices'][0]['finish_reason'];providers[q.get('provider')][finish]+=1
                        if row['data']['seconds']>45:over_deadline.append({'case':result['case'],'task':result['task'],'seconds':row['data']['seconds'],'trace_sha256':result['trace_sha256']})
                if row['kind']=='before':before=row['data']['state']
                if row['kind']=='selected' and result['task']=='combat':
                    c=row['data']['choice']
                    if c['action']['action']=='end_turn':
                        observations[arm]['end_turns']+=1
                        playable=[x for x in before.get('hand',[]) if x.get('can_play')]
                        if before.get('energy',0)>0 and playable:
                            observations[arm]['end_turn_with_energy_and_playable_card']+=1
                            if arm=='jev':examples.append({'case':result['case'],'round':before.get('round'),'energy':before.get('energy'),'cards':[x['name'] for x in playable],
                                                         'state_sha256':digest(before),'trace_sha256':result['trace_sha256']})
        lat=[r['seconds'] for r in responses];usages=[r['response'].get('usage',{}) for r in responses]
        costs=[u.get('cost') for u in usages]
        metrics[arm]={'requests':requests,'response_count':len(responses),'invalid_responses':bad,
            'cost_usd':sum(c for c in costs if c is not None),'billing_known':len(costs)==requests and all(c is not None for c in costs),
            'p50_seconds':statistics.median(lat) if lat else None,'p95_seconds':percentile(lat,.95),
            'prompt_tokens':sum(u.get('prompt_tokens',u.get('input_tokens',0)) for u in usages),
            'completion_tokens':sum(u.get('completion_tokens',u.get('output_tokens',0)) for u in usages),
            'reported_reasoning_tokens':sum(u.get('completion_tokens_details',{}).get('reasoning_tokens',0) for u in usages),
            'models':sorted({str(r['response'].get('model')) for r in responses})}
        if arm!='program':
            ledger=report['ledgers'][arm]
            if requests!=ledger['calls'] or abs(metrics[arm]['cost_usd']-ledger['cost'])>1e-9:failures.append('ledger mismatch '+arm)
    index={(r['case'],r['task'],r['arm']):r for r in results}
    for c in fixtures['cases']:
        for task in ['combat','reward']:
            p=index[(c['id'],task,'program')];j=index[(c['id'],task,'jev')]
            pairs.append({'case':c['id'],'cohort':c['config']['cohort'],'task':task,
                          'program':[p['status'],p.get('final_hp')],'jev':[j['status'],j.get('final_hp')],
                          'jev_vs_program':paired(p,j,task)})
    for c in sorted({r['character'] for r in results}):
        by_character[c]={}
        for arm in ['program','jev']:
            rs=[r for r in results if r['character']==c and r['arm']==arm and r['task']=='combat']
            by_character[c][arm]={'n':len(rs),'wins':sum(r['status']=='win' for r in rs)}
    gates={}
    for arm in ['jev','deepseek']:
        s=report['summary'][f'confirm/combat/{arm}'];p=s['comparisons']['program'];ct=p['pairs']
        valid=sum(ct.get(k,0) for k in ['better','worse','tie'])
        quality=valid>=19 and p['treatment_wins']>=p['baseline_wins'] and ct.get('better',0)>=6 and ct.get('worse',0)<=2 and (p['median_hp_delta'] or 0)>=3
        speed=s['p95_seconds'] is not None and s['p95_seconds']<=15
        cost=metrics[arm]['billing_known'] and s['mean_cost_per_completed'] is not None and s['mean_cost_per_completed']<=.05
        reward=report['summary'][f'confirm/reward/{arm}']['comparisons']['program']['pairs']
        reward_quality=sum(reward.get(k,0) for k in ['better','worse','tie'])>=19 and reward.get('better',0)>=6 and reward.get('worse',0)<=2
        replace=None
        if arm=='deepseek':
            q=s['comparisons']['jev'];x=q['pairs']
            replace=q['treatment_wins']>=q['baseline_wins'] and x.get('better',0)>=6 and x.get('worse',0)<=2
        gates[arm]={'valid_locked_combat_pairs':valid,'combat_quality_pass':quality,'speed_pass':speed,'cost_pass':cost,
                    'reward_quality_pass':reward_quality,'replace_jev_quality_pass':replace,
                    'decision':'do_not_promote','reason':'quality gate failed' if arm=='jev' else 'pilot reliability exit; strength unmeasured'}
    out={'experiment':'E113','tested_sha':report['manifest']['code_commit'],'results_sha256':hashlib.sha256((D/'results.json').read_bytes()).hexdigest(),
         'cells':len(results),'source_traces_checked':len(fixtures['cases']),
         'verified_trace_count':trace_count,'verified_replay_count':parity,'integrity_failures':failures,
         'metrics':metrics,'gates':gates,'providers':dict(providers),'protocol_deadline_violations':over_deadline,
         'end_turn_observations':dict(observations),'end_turn_caveat':'These are screening observations, not proofs that every such end-turn is harmful.',
         'jev_end_turn_examples':examples,'by_character_all_six_seeds':by_character,'pairs':pairs}
    (D/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['cells','verified_trace_count','verified_replay_count','integrity_failures','metrics','gates','end_turn_observations','by_character_all_six_seeds']},indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
