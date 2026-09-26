"""Real engine compatibility probes. Synthetic controls are explicitly separate."""
import argparse
import hashlib
import json
import time
import uuid
from rsi.engine import ROOT, Headless, action
from rsi.full import macro_candidates
from rsi.potions import with_potions
from rsi.resources import legacy_projection, inventory
from rsi.trace import Trace, digest, version_manifest


def probe(case, mode, manifest, fixture_hash):
    resources=mode!='legacy'
    uid=str(uuid.uuid4());result={'kind':case['kind'],'character':case['character'],'mode':mode,
        'synthetic':mode.startswith('synthetic'),'status':'error','checks':{},'seed':case['seed']}
    trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,'experiment':'E093','fixture_sha256':fixture_hash,**result})
    started=time.monotonic();engine=None
    try:
        engine=Headless(trace.directory,resource_decisions=resources)
        def send(command):
            trace.write('command',command)
            state=engine.send(command);trace.write('state',state);return state
        def check(name,condition):
            result['checks'][name]=bool(condition)
            if not condition:raise AssertionError(name)
        def drain(state):
            while state.get('decision')=='potion_reward':
                state=send(action('claim_potion_reward' if state['can_claim'] else 'skip_potion_reward'))
            return state
        state=send({'cmd':'start_run','character':case['character'],'ascension':case['ascension'],'seed':case['seed']})
        for command in case['prefix_actions']:
            state=drain(state);state=send(command)
        state=drain(state)
        result['entry_hash']=digest(legacy_projection(state))
        check('legacy_entry_parity',result['entry_hash']==case['legacy_state_hash'])
        if mode=='legacy':
            result['status']='compatible'
        elif case['kind']=='combat':
            check('capacity_exported',isinstance(state['player']['potion_capacity'],int))
            if mode=='synthetic_selection':
                update=send({'cmd':'set_player','potions':['GAMBLERS_BREW','FAIRY_IN_A_BOTTLE']})
                state['player']=update['player']
                options=with_potions(state,[])
                check('automatic_excluded',all(c['details']['usage']!='Automatic' for c in options))
                chosen=next(c for c in options if c['details']['id']=='GAMBLERS_BREW')
            else:
                options=with_potions(state,[])
                check('legal_manual_potion_available',bool(options));chosen=options[0]
            before=inventory(state);result['selected']=chosen
            result['before_potions']=before
            state=send(chosen['action'])
            boundaries=[]
            for _ in range(8):
                if state.get('decision') not in ('card_select','card_reward'):break
                boundaries.append(state['decision']);choices=macro_candidates(state,resource_decisions=True)
                state=send(choices[0]['action'])
            result['selection_boundaries']=boundaries
            result['after_potions']=inventory(state)
            check('potion_consumed',len(inventory(state))==len(before)-1)
            if mode=='synthetic_selection':check('selection_exercised',bool(boundaries))
            result['status']='compatible'
        elif case['kind']=='shop':
            if not state['player']['has_open_potion_slots']:
                before=len(inventory(state));p=next(p for p in state['player']['potions'] if p['can_discard'])
                state=send(action('discard_potion',potion_index=p['index']))
                check('discard_frees_slot',len(inventory(state))==before-1 and state['player']['has_open_potion_slots'])
            choice=next(c for c in macro_candidates(state,resource_decisions=True) if c['action']['action']=='buy_potion')
            before=inventory(state);gold=state['player']['gold'];price=choice['details']['cost']
            state=send(choice['action']);result.update(purchase=choice,before_potions=before,after_potions=inventory(state),gold_before=gold,gold_after=state['player']['gold'])
            check('advertised_price_paid',gold-state['player']['gold']==price)
            check('advertised_potion_acquired',choice['details']['id'] in inventory(state) and len(inventory(state))==len(before)+1)
            result['status']='compatible'
        else:
            if mode=='synthetic_full_reward':
                update=send({'cmd':'set_player','potions':['STRENGTH_POTION','FAIRY_IN_A_BOTTLE']})
                state['player']=update['player']
            state=send(case['trigger_action']);result['boundary']=state['decision']
            if case['kind']=='reward_full' and state['decision']!='potion_reward':
                result['status']='no_potion_drop';return result
            check('explicit_potion_reward',state['decision']=='potion_reward')
            result['reward']=state['potion']
            if not state['player']['has_open_potion_slots']:
                cs=macro_candidates(state,resource_decisions=True)
                check('no_claim_when_full',not any(c['action']['action']=='claim_potion_reward' for c in cs))
                previous=inventory(state);discard=next(c for c in cs if c['action']['action']=='discard_potion')
                state=send(discard['action']);check('reward_survives_discard',state['decision']=='potion_reward' and state['can_claim'])
                check('discard_removed_one',len(inventory(state))==len(previous)-1)
            before=inventory(state);reward=state['potion']['id']
            state=send(action('claim_potion_reward'))
            check('reward_potion_received',reward in inventory(state) and len(inventory(state))==len(before)+1)
            check('reward_continues',state['decision']!='potion_reward')
            if case['kind']=='reward_space' and not result['synthetic']:
                check('legacy_after_claim_parity',digest(legacy_projection(state))==case['legacy_after_hash'])
            result['status']='compatible'
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',result['error'])
    finally:
        if engine:engine.close()
        result['seconds']=round(time.monotonic()-started,3)
        trace.write('summary',result);result['trace_path']=str(trace.path.relative_to(ROOT));result['trace_sha256']=trace.close()
        result['trace_verified']=hashlib.sha256(trace.path.read_bytes()).hexdigest()==result['trace_sha256']
        print(json.dumps({k:v for k,v in result.items() if k not in ('selected','purchase','reward')},ensure_ascii=False),flush=True)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before evaluation')
    f=(ROOT/'experiments/E093/fixtures.json').read_bytes();cases=json.loads(f)['cases'];fh=hashlib.sha256(f).hexdigest()
    results=[probe(c,mode,manifest,fh) for c in cases for mode in ('legacy','resources')]
    results.append(probe(next(c for c in cases if c['kind']=='combat'),'synthetic_selection',manifest,fh))
    results.append(probe(next(c for c in cases if c['kind']=='reward_space'),'synthetic_full_reward',manifest,fh))
    (ROOT/a.output).write_text(json.dumps({'manifest':manifest,'fixture_sha256':fh,'results':results},indent=2)+'\n')
    if any(r['status']=='error' for r in results):raise SystemExit(1)


if __name__=='__main__':main()
