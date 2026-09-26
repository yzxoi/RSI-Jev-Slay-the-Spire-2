"""Real CLI Boss continuations: Jev actions, entry plan, task-mediated Astra owner."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from rsi.engine import ROOT, Headless
from rsi.full import STRATEGY, macro_candidates
from rsi.jev import Budget, Jev
from rsi.numerical import intent_damage
from rsi.policy import combat_candidates, model_state
from rsi.potions import with_potions
from rsi.room_owner import RoomOwner, route_entry
from rsi.teacher import terminal
from rsi.trace import Trace, digest, version_manifest

D = ROOT / 'experiments/E099'


def choices_for(state):
    return with_potions(state, combat_candidates(state)) if state['decision'] == 'combat_play' else macro_candidates(state)


def state_input(state, recent, plan=None):
    payload = {'state': model_state(state), 'strategy': STRATEGY, 'recent_actions': recent[-6:],
               'computed': {'current_visible_incoming_before_new_plays': sum(intent_damage(e) for e in state.get('enemies', [])),
                            'limitation': 'Not a simulation; killing, weakness, block, retaliation and other powers can change damage.'}}
    if plan:
        payload['astra_room_plan'] = plan
    return payload


def committed_response(path, root=ROOT):
    """An appearing untracked/staged packet is not ready; bind immutable commit bytes."""
    if not path.exists():
        return None
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root).strip():
        return None
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    result = subprocess.run(['git', 'show', f'{commit}:{path.relative_to(root)}'], cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode or result.stdout != path.read_bytes():
        return None
    return json.loads(result.stdout), commit


def battle(case, mode, label):
    manifest = version_manifest()
    if manifest['tracked_dirty']:
        raise RuntimeError('Commit implementation/teacher iteration before evaluation')
    if manifest['game_dll_sha256'] != '9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4':
        raise RuntimeError('Pinned game mismatch')
    uid = str(uuid.uuid4())
    trace = Trace(ROOT / 'artifacts/runs' / uid, {**manifest, 'experiment': 'E099', 'case': case['id'],
                  'mode': mode, 'label': label, 'scope': 'boss_only_task_mediated_expert'})
    out = {'run_id': uid, 'case': case['id'], 'mode': mode, 'label': label, 'manifest': manifest,
           'status': 'error', 'steps': 0, 'expert_packets': 0, 'expert_input_chars': 0,
           'expert_output_chars': 0, 'expert_api_tokens': None, 'expert_cost_usd': None}
    budget = Budget(240, .20, conservative_failures=True)
    engine = None; state = {}; recent = []; transitions = []; metas = []; start = time.monotonic()
    plan = json.loads((D / 'plans.json').read_text())[case['id']] if mode == 'plan' else None
    out['offline_plan_calls'] = int(bool(plan)); out['offline_plan_chars'] = len(json.dumps(plan)) if plan else 0
    try:
        engine = Headless(trace.directory)
        for command in case['commands']:
            state = engine.send(command)
        out['entry_verified'] = digest(state) == case['entry_hash']
        if not out['entry_verified']: raise RuntimeError('Frozen entry mismatch')
        trace.write('entry', {'state': state, 'state_hash': digest(state), 'route_shadow': route_entry(state)})
        owner = RoomOwner(state, mode)
        jev = Jev(budget) if mode != 'astra' else None
        for step in range(241):
            status = terminal(state)
            if status:
                out['status'] = status; break
            if step == 240 or time.monotonic() - start > (7200 if mode == 'astra' else 900):
                out['status'] = 'budget_exhausted'; break
            choices = choices_for(state)
            trace.write('before', {'state': state, 'state_hash': digest(state)})
            trace.write('candidates', choices)
            payload = state_input(state, recent, plan)
            if len(choices) == 1:
                chosen = choices[0]; provenance = 'only_legal_choice'
            elif mode != 'astra':
                chosen, meta = jev.choose(payload, choices, trace); metas.append(meta); provenance = mode
            else:
                chosen = owner.next(state, choices)
                while chosen is None:
                    seq = out['expert_packets'] + 1
                    if seq > 80: raise RuntimeError('Expert 80 packet budget exhausted')
                    request = {'case': case['id'], 'seq': seq, 'state_hash': digest(state), 'payload': payload,
                               'candidates': choices, 'owner': 'astra', 'exit': 'boss defeat or reward boundary'}
                    pending = trace.directory / 'request.tmp'
                    pending.write_text(json.dumps(request, indent=2) + '\n')
                    pending.replace(trace.directory / 'request.json')
                    trace.write('expert_request', request)
                    print(json.dumps({'waiting': case['id'], 'seq': seq, 'run_id': uid,
                                      'round': state.get('round'), 'hp': state.get('player', {}).get('hp')}), flush=True)
                    path = D / 'teacher' / case['id'] / f'{seq:03}.json'
                    until = time.monotonic() + 1800
                    committed = None
                    while committed is None:
                        if time.monotonic() > until: raise TimeoutError('Committed expert response timeout')
                        committed = committed_response(path)
                        if committed is None: time.sleep(.25)
                    packet, response_commit = committed
                    if packet.get('seq') != seq: raise RuntimeError('Expert sequence mismatch')
                    owner.accept(packet, state)
                    out['expert_packets'] += 1
                    out['expert_input_chars'] += len(json.dumps(request, ensure_ascii=False))
                    out['expert_output_chars'] += len(json.dumps(packet, ensure_ascii=False))
                    trace.write('expert_response', {'packet': packet, 'commit': response_commit})
                    chosen = owner.next(state, choices)
                    if chosen is None: raise ValueError('Teacher first action illegal')
                provenance = 'astra'
            if chosen not in choices: raise RuntimeError('Illegal fresh action')
            trace.write('selected', {'choice': chosen, 'owner': mode, 'provenance': provenance})
            before = state
            state = engine.send(chosen['action'])
            owner.observed(before, state)
            trace.write('after', {'state': state, 'state_hash': digest(state)})
            recent.append({'round': before.get('round'), 'choice': chosen})
            transitions.append([digest(before), chosen['action'], digest(state)])
            out['steps'] = step + 1
    except Exception as exc:
        out['error'] = f'{type(exc).__name__}: {exc}'
        trace.write('failure', out['error'])
    finally:
        if engine: engine.close()
    out.update(seconds=round(time.monotonic()-start, 3), final_hp=state.get('player', {}).get('hp'),
               final_round=state.get('round'), final_state_hash=digest(state),
               remaining_enemies=[{'name':e['name'],'hp':e['hp']} for e in state.get('enemies',[])],
               model_calls=budget.calls, model_cost_usd=budget.spent-budget.estimated_usd,
               unknown_model_calls=budget.uncertain_calls, model_budgeted_usd=budget.spent,
               model_seconds=sum(m['seconds'] for m in metas),
               models=sorted(set(m['model'] for m in metas if m.get('model'))),
               trajectory_sha256=digest(transitions),
               wire_sha256=hashlib.sha256((trace.directory/'wire.jsonl').read_bytes()).hexdigest() if engine else None)
    trace.write('summary', out)
    out['trace_path'] = str(trace.path.relative_to(ROOT)); out['trace_sha256'] = trace.close()
    (trace.directory/'result.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out), flush=True)
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode', choices=['students','astra'], required=True)
    ap.add_argument('--case', choices=['ironclad','silent']);ap.add_argument('--label',default='pilot-01');a=ap.parse_args()
    cases=json.loads((D/'fixtures.json').read_text())['cases']
    if a.case:cases=[c for c in cases if c['id']==a.case]
    if a.mode=='students':
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(battle,c,m,a.label) for c in cases for m in ['jev','plan']]
            results=[f.result() for f in futures]
    else:
        results=[battle(c,'astra',a.label) for c in cases]
    path=ROOT/'artifacts/runs'/f'e099-{a.mode}-{a.case or "all"}-{a.label}.json'
    path.write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
