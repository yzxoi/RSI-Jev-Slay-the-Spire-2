"""Opt-in paired Boss experiments with per-run and shared model budgets."""
import hashlib
import json
import time
import uuid
from .engine import ROOT, Headless
from .jev import Budget, Jev
from .potion_contract import PotionContract
from .lethal_certificate import certify
from .turn_advisor import TurnAdvisor
from .teacher import terminal
from .trace import Trace, digest, version_manifest
from scripts.evaluate_routing_e099 import choices_for, state_input


class PairedBudget:
    def __init__(self, session):
        self.local=Budget(240,.20,conservative_failures=True);self.session=session
    def acquire(self):
        # Evaluations are sequential; release a session reservation if local cap blocks.
        self.session.acquire()
        try:self.local.acquire()
        except Exception:
            self.session.settle({'cost':0});raise
    def settle(self, usage):
        self.local.settle(usage);self.session.settle(usage)


def battle(case, arm, repeat, experiment, session, *, contract=None, lethal=False, turn_advice=False):
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit changes before evaluation')
    if manifest['game_dll_sha256']!='9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':raise ValueError('Wrong game build')
    uid=str(uuid.uuid4());config={'experiment':experiment,'case':case['id'],'arm':arm,'repeat':repeat,'run_id':uid,'contract':contract,'lethal':lethal,'turn_advice':turn_advice}
    trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,**config})
    out={**config,'manifest':manifest,'status':'error','steps':0,'program_actions':0,'lethal_actions':0,'lethal_probes':[]}
    plan=json.loads((ROOT/'experiments/E099/plans.json').read_text())[case['id']]
    engine=None;state={};budget=PairedBudget(session);recent=[];trans=[];calls=[];start=time.monotonic();last_round=0;pc=None;advisor=None;prefix=list(case['commands'])
    try:
        engine=Headless(trace.directory)
        for cmd in case['commands']:state=engine.send(cmd)
        if digest(state)!=case['entry_hash']:raise ValueError('Entry mismatch')
        out['entry_verified']=True;trace.write('entry',{'state':state,'state_hash':digest(state)})
        pc=PotionContract(state,contract) if contract else None
        advisor=TurnAdvisor(case['id'],trace,experiment,state['context']) if turn_advice else None
        jev=Jev(budget)
        for step in range(241):
            status=terminal(state)
            if status:out['status']=status;break
            if step==240 or time.monotonic()-start>(7200 if turn_advice else 900):out['status']='budget_exhausted';break
            last_round=state.get('round',last_round)
            choices=choices_for(state);allowed=choices;chosen=None;evidence={};source='jev';proof=None
            trace.write('before',{'state':state,'state_hash':digest(state)});trace.write('candidates',choices)
            if lethal:
                chosen,proof,probes=certify(state,choices,prefix,manifest,uid)
                out['lethal_probes'].extend(probes);trace.write('lethal_check',probes)
                if chosen:source='certified_lethal'
            if pc and chosen is None:
                chosen,allowed,evidence=pc.prepare(state,choices)
                trace.write('resource_contract',evidence)
                if chosen:source='potion_contract'
            trace.write('allowed_candidates',allowed)
            if chosen is None:
                if len(allowed)==1:chosen=allowed[0];source='only_legal_choice'
                else:
                    payload=state_input(state,recent,plan)
                    if advisor:
                        payload['astra_turn_plan']=advisor.update(state,recent,plan)
                        trace.write('turn_plan_applied',{'round':advisor.round,'commit':advisor.commit,'state_hash':digest(state)})
                    chosen,meta=jev.choose(payload,allowed,trace);calls.append(meta)
            if chosen not in choices:raise ValueError('Action not legal')
            trace.write('selected',{'choice':chosen,'source':source})
            before=state;state=engine.send(chosen['action']);prefix.append(chosen['action'])
            if source=='certified_lethal':
                if digest(state)!=proof['after_hash'] or terminal(state)!='boss_clear':raise ValueError('Canonical lethal differs from certificate')
                out['lethal_actions']+=1
            if source=='potion_contract':pc.accepted(evidence['rule_id'],before,state);out['program_actions']+=1
            trace.write('after',{'state':state,'state_hash':digest(state)})
            recent.append({'round':before.get('round'),'choice':chosen})
            trans.append([digest(before),chosen['action'],digest(state)]);out['steps']=step+1
    except Exception as exc:
        out['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',out['error'])
    finally:
        if engine:engine.close()
    b=budget.local
    out.update(expert_packets=advisor.requests if advisor else 0,expert_input_chars=advisor.input_chars if advisor else 0,
               expert_output_chars=advisor.output_chars if advisor else 0,expert_wait_seconds=advisor.seconds if advisor else 0,
               expert_tokens=None,expert_cost_usd=None)
    out.update(final_hp=state.get('player',{}).get('hp'),last_round=last_round,seconds=round(time.monotonic()-start,3),
               model_calls=b.calls,model_cost_usd=b.spent-b.estimated_usd,unknown_model_calls=b.uncertain_calls,
               budgeted_usd=b.spent,model_seconds=sum(c['seconds'] for c in calls),models=sorted({c['model'] for c in calls if c.get('model')}),
               fulfilled=sorted(pc.done) if pc else [],trajectory_sha256=digest(trans),final_state_hash=digest(state),
               wire_sha256=hashlib.sha256((trace.directory/'wire.jsonl').read_bytes()).hexdigest() if engine else None)
    trace.write('summary',out);out['trace_path']=str(trace.path.relative_to(ROOT));out['trace_sha256']=trace.close()
    (trace.directory/'result.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out.get(k) for k in ['case','arm','repeat','status','final_hp','model_calls','model_cost_usd','program_actions','error']}),flush=True)
    return out
