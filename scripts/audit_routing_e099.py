"""Reconcile every E099 action with raw wire, legal candidates and teacher commits."""
from collections import Counter
import hashlib
import json
import subprocess
from rsi.engine import ROOT
from rsi.policy import combat_candidates
from rsi.guard import filter_end_turn
from rsi.room_owner import route_entry
from rsi.teacher import terminal
from rsi.trace import digest

D=ROOT/'experiments/E099'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    fixtures=json.loads((D/'fixtures.json').read_text())['cases']; cases={c['id']:c for c in fixtures}
    results=[]
    for name in ['e099-students-all-pilot-01.json','e099-astra-ironclad-pilot-01.json','e099-astra-silent-pilot-01.json']:
        results.extend(json.loads((ROOT/'artifacts/runs'/name).read_text()))
    assert Counter((r['case'],r['mode']) for r in results)==Counter((c,m) for c in cases for m in ['jev','plan','astra'])
    audits=[];diagnostics=[]
    for r in results:
        p=ROOT/r['trace_path'];rows=[json.loads(l) for l in p.read_text().splitlines()]
        wire=p.with_name('wire.jsonl');wr=[json.loads(l) for l in wire.read_text().splitlines()]
        commands=[x['data'] for x in wr if x['kind']=='command']
        responses=[x['data'] for x in wr if x['kind']=='state' and x['data'].get('type')!='ready']
        case=cases[r['case']];prefix=len(case['commands'])
        entry=next(x['data']['state'] for x in rows if x['kind']=='entry')
        checks={'trace_hash':sha(p)==r['trace_sha256'],'wire_hash':sha(wire)==r['wire_sha256'],
                'exact_entry':digest(entry)==case['entry_hash']==digest(responses[prefix-1]),
                'exact_prefix':commands[:prefix]==case['commands'],
                'no_debug':all(c.get('cmd') in ('start_run','action') for c in commands),
                'state_chain':True,'fresh_legal':True,'owner_continuity':True,'expert_binding':True,
                'teacher_committed':True,'terminal_scope':True}
        trans=[];state=entry;choices=[];chosen=None;before=None;packet=None;expert_count=0
        ends=[];potion_uses=[];pact=[];rounds=[];last=entry;guard_checks=[]
        for row in rows:
            k,v=row['kind'],row['data']
            if k=='before':
                before=v['state'];checks['state_chain'] &= digest(before)==v['state_hash']==digest(state)
                if before.get('decision')=='combat_play':
                    last=before;rounds.append(before['round'])
            elif k=='candidates':choices=v
            elif k=='expert_request':
                packet=v;checks['expert_binding'] &= v['state_hash']==digest(before)
            elif k=='expert_response':
                ep=v['packet'];expert_count+=1
                checks['expert_binding'] &= ep['state_hash']==packet['state_hash'] and ep['seq']==packet['seq']
                path=f"experiments/E099/teacher/{r['case']}/{ep['seq']:03}.json"
                committed=json.loads(subprocess.check_output(['git','show',f"{v['commit']}:{path}"],cwd=ROOT))
                checks['teacher_committed'] &= committed==ep
            elif k=='selected':
                chosen=v['choice'];checks['fresh_legal'] &= chosen in choices
                checks['owner_continuity'] &= v['owner']==r['mode'] and v['provenance'] in (r['mode'],'only_legal_choice')
                if chosen['action']['action']=='end_turn':
                    playable=[c['name'] for c in before.get('hand',[]) if c.get('can_play')]
                    _,guard=filter_end_turn(before,combat_candidates(before))
                    ends.append({'round':before.get('round'),'energy':before.get('energy'),'hp':before['player']['hp'],
                                 'playable_cards':playable,'potions':[p['name'] for p in before['player']['potions']],
                                 'existing_guard':guard})
                if chosen['action']['action']=='use_potion':potion_uses.append({'name':chosen['name'],'round':before.get('round')})
                if chosen['name']=="Pact's End":pact.append({'round':before.get('round'),'before_enemy_hp':[(e['name'],e['hp']) for e in before['enemies']]})
            elif k=='after':
                state=v['state'];i=len(trans)
                checks['state_chain'] &= digest(state)==v['state_hash']
                checks['state_chain'] &= commands[prefix+i]==chosen['action'] and responses[prefix+i]==state
                trans.append([digest(before),chosen['action'],digest(state)])
                if chosen['name']=="Pact's End":pact[-1]['after_enemy_hp']=[(e['name'],e['hp']) for e in state.get('enemies',[])]
                if i<len(commands)-prefix-1:checks['terminal_scope'] &= terminal(state) is None
        checks['transition_hash']=digest(trans)==r['trajectory_sha256']
        checks['all_actions_counted']=len(trans)==r['steps']==len(commands)-prefix and len(commands)==len(responses)
        checks['terminal_scope'] &= terminal(state)==r['status']
        checks['expert_count']=expert_count==r['expert_packets']
        r['last_combat_round']=max(rounds);r['last_combat_enemies']=[{'name':e['name'],'hp':e['hp']} for e in last['enemies']]
        diag={'case':r['case'],'mode':r['mode'],'end_turns':ends,'potions_used':potion_uses,
              'end_turns_with_energy_and_playable_cards':sum(e['energy']>0 and bool(e['playable_cards']) for e in ends),
              'end_turns_existing_guard_would_block':sum(e['existing_guard']['excluded'] for e in ends),
              'unspent_potions_last_combat':[p['name'] for p in last['player']['potions']],
              'pacts_end_observations':pact}
        diagnostics.append(diag);audits.append({'run_id':r['run_id'],'case':r['case'],'mode':r['mode'],'checks':checks,'passed':all(checks.values())})
    shadow=[next(r for r in results if r['case']==c['id'] and r['mode']==route_entry(c['entry'])['mode']) for c in fixtures]
    output={'experiment':'E099','scope':'Two development Boss entries, six first-pass continuations; not full runs or independent holdout.',
            'fixture_sha256':sha(D/'fixtures.json'),'plans_sha256':sha(D/'plans.json'),'results':results,
            'summary_by_mode':{m:{'clears':sum(r['status']=='boss_clear' for r in results if r['mode']==m),
                                  'battles':2,'model_calls':sum(r['model_calls'] for r in results if r['mode']==m),
                                  'model_cost_usd':sum(r['model_cost_usd'] for r in results if r['mode']==m),
                                  'expert_packets':sum(r['expert_packets'] for r in results if r['mode']==m)} for m in ['jev','plan','astra']},
            'shadow_composition':{'scope':'Frozen paired-row composition, not additional trials or online routing',
                                  'run_ids':[r['run_id'] for r in shadow],'clears':sum(r['status']=='boss_clear' for r in shadow),
                                  'gate':{c['id']:route_entry(c['entry']) for c in fixtures}},
            'expert_total_cost_known':False,'diagnostics':diagnostics,
            'limitations':['Existing production planner not rerun as a baseline.', 'Raw Jev candidates are unfiltered; existing end-turn guard was applied only diagnostically and abstains on Minion/Plating.',
                           'Entry plans contain advice, not executable constraints; failure cannot separate model inability from interface failure.',
                           'One sample per arm, shared Boss/seed, historical development entries, no generalization or total-cost advantage.']}
    audit={'runs':len(results),'checks_per_run':audits,'all_passed':all(a['passed'] for a in audits)}
    (D/'result.json').write_text(json.dumps(output,indent=2)+'\n');(D/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'audit':audit['all_passed'],'results':output['summary_by_mode'],'shadow_clears':output['shadow_composition']['clears'],
                      'end_turn_diagnostics':[{k:d[k] for k in ['case','mode','end_turns_with_energy_and_playable_cards','end_turns_existing_guard_would_block','potions_used','unspent_potions_last_combat']} for d in diagnostics]},indent=2))

if __name__=='__main__':main()
