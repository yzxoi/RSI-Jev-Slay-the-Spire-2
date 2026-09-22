"""Full-run headless evaluation, with separate macro and combat decisions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import itertools
import json
from pathlib import Path
import time
import uuid
from .engine import ROOT, CHARACTERS, Headless, action
from .jev import Budget, Jev
from .numerical import computed_candidates, greedy_choice
from .policy import combat_candidates, model_state
from .trace import Trace, digest, version_manifest

STRATEGY = """Maximize probability of completing all three acts. Evaluate current deck, next threats and resources. Early decks need efficient damage, then reliable block, draw/energy and scaling for bosses. Prefer cards that solve a concrete gap; skipping mediocre rewards is valid. Do not force a named archetype. Remove curses/weak starters when affordable. Rest when healing is needed to survive upcoming threats; otherwise upgrades have lasting value. Avoid risky elites with low health/weak damage. Buy useful relics/cards rather than spending all gold indiscriminately. For card selection interpret the preceding action and scene: removing, upgrading, discarding and exhausting require different choices. Supplied rules are authoritative; descriptions with placeholders use the supplied stats. Numerical combat previews are limited, not full simulation."""


def macro_candidates(state, history=None):
    d = state.get('decision'); out = []
    def add(name, metadata=None, **args):
        out.append({'action': action(name, **args), 'name': name, 'details': metadata})
    if d == 'map_select':
        for c in state.get('choices', []): add('select_map_node', c, col=c['col'], row=c['row'])
    elif d in ['event_choice', 'rest_site']:
        for c in state.get('options', []):
            if not c.get('is_locked') and c.get('is_enabled', True): add('choose_option', c, option_index=c['index'])
        if not out: add('leave_room')
    elif d == 'card_reward':
        for c in state.get('cards', []): add('select_card_reward', c, card_index=c['index'])
        if state.get('can_skip', True): add('skip_card_reward')
    elif d == 'bundle_select':
        for i, c in enumerate(state.get('bundles', [])): add('select_bundle', c, bundle_index=c.get('index', i))
    elif d == 'card_select':
        cards = state.get('cards', []); lo = state.get('min_select', 1); hi = state.get('max_select', 1)
        for n in range(max(1, lo), min(len(cards), hi) + 1):
            for combo in itertools.islice(itertools.combinations(cards, n), 128):
                add('select_cards', [{'index':c['index'],'name':c.get('name'),'id':c.get('id')} for c in combo], indices=','.join(str(c['index']) for c in combo))
            if len(out) >= 128: break
        if lo == 0: add('skip_select')
    elif d == 'shop':
        gold = state['player']['gold']
        for key, cmd, arg in [('cards','buy_card','card_index'),('relics','buy_relic','relic_index'),('potions','buy_potion','potion_index')]:
            # Potion capacity is not exported by this pinned headless serializer.
            if key == 'potions': continue
            for c in state.get(key, []):
                if c.get('is_stocked') and c['cost'] <= gold: add(cmd, c, **{arg:c['index']})
        price = state.get('card_removal_cost')
        if price is not None and price <= gold and not (history or {}).get('removed_here'): add('remove_card', {'price':price})
        add('leave_room')
    elif d == 'unknown': add('proceed')
    else: raise RuntimeError(f'Unsupported macro decision: {d}')
    for i, c in enumerate(out): c['id'] = f'a{i:03}'
    if not out: raise RuntimeError(f'No candidates for {d}')
    return out


def fixed_macro(state, choices):
    d=state['decision']; player=state.get('player', {})
    if d=='shop': return choices[-1]
    if d=='map_select':
        hp=player.get('hp',0)/max(1,player.get('max_hp',1))
        rank={'RestSite': 8 if hp<.6 else 4,'Rest':8 if hp<.6 else 4,'Treasure':9,'Shop':5 if player.get('gold',0)>150 else -1,'Monster':3,'Unknown':2,'Event':2,'Elite':-3,'Boss':0}
        return max(choices,key=lambda c:rank.get((c.get('details') or {}).get('type'),0))
    if d=='rest_site':
        preferred='HEAL' if player.get('hp',0)<player.get('max_hp',1)*.65 else 'SMITH'
        return next((c for c in choices if (c.get('details') or {}).get('option_id')==preferred),choices[0])
    return choices[0]


def episode(config, manifest, jev=None):
    uid=str(uuid.uuid4()); trace=Trace(ROOT/'artifacts/runs'/uid,{**manifest,**config,'run_id':uid,'scope':'complete_run'})
    result={**config,'run_id':uid,'status':'error','steps':0,'model_calls':0,'cost_usd':0.0}; scenes=Counter(); engine=None; state={}; start=time.monotonic(); history={}; unchanged=0; last=None
    try:
        engine=Headless(trace.directory)
        state=engine.send({'cmd':'start_run','character':config['character'],'ascension':config['ascension'],'seed':config['seed']})
        result['initial_state_hash']=digest(state)
        for step in range(config.get('max_steps',4000)):
            result['steps']=step; d=state.get('decision'); scenes[d]+=1
            if d=='game_over':
                result['status']='victory' if state.get('victory') else 'normal_defeat';break
            h=digest(state); unchanged=unchanged+1 if last==h else 0;last=h
            if unchanged>=5: raise RuntimeError('No state progress in six successive decisions')
            trace.write('before',{'state':state,'state_hash':h})
            if d=='combat_play':
                choices=combat_candidates(state)
                if config['policy']=='first': selected=choices[0]
                else:
                    choices=computed_candidates(state,choices); selected=greedy_choice(state,choices)
            else:
                choices=macro_candidates(state,history)
                if config['policy']!='hybrid' or len(choices)==1: selected=fixed_macro(state,choices)
                else:
                    context={'state':model_state(state),'strategy':STRATEGY,'previous_decision':history.get('previous')}
                    selected,call=jev.choose(context,choices,trace)
                    result['model_calls']+=1; result['cost_usd']+=call['usage'].get('cost',0)
            trace.write('candidates',choices);trace.write('selected',selected)
            if d=='map_select':history['removed_here']=False
            if selected['action']['action']=='remove_card':history['removed_here']=True
            if d!='card_select':history['previous']={'scene':d,'choice':selected}
            state=engine.send(selected['action']);trace.write('after',{'state':state,'state_hash':digest(state)})
        else: raise TimeoutError('Full-run step budget exhausted')
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}';trace.write('failure',{'error':result['error']})
    finally:
        if engine:
            engine.close()
            diagnostic=(trace.directory/'engine.stderr.log').read_text()
            if 'forcing game_over' in diagnostic:
                result['status']='error';result['error']='Upstream forced game_over after deadlock; not a normal defeat'
            result['engine_log_sha256']=__import__('hashlib').sha256(diagnostic.encode()).hexdigest()
    context=state.get('context') or {}
    result.update(act=state.get('act',context.get('act')),floor=state.get('floor',context.get('floor')),final_decision=state.get('decision'),final_hp=state.get('player',{}).get('hp'),seconds=round(time.monotonic()-start,3),scenes=dict(scenes))
    trace.write('summary',result);result['trace_path']=str(trace.path.relative_to(ROOT));result['trace_sha256']=trace.close();print(json.dumps(result),flush=True);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--characters',default=','.join(CHARACTERS));p.add_argument('--seeds',default='full_dev_001');p.add_argument('--policies',default='first,greedy');p.add_argument('--ascension',type=int,default=10);p.add_argument('--workers',type=int,default=3);p.add_argument('--max-calls',type=int,default=12000);p.add_argument('--max-usd',type=float,default=3);p.add_argument('--output',required=True);a=p.parse_args()
    chars=a.characters.split(','); policies=a.policies.split(',')
    if set(chars)-set(CHARACTERS) or set(policies)-{'first','greedy','hybrid'}:p.error('Invalid character or policy')
    manifest=version_manifest()
    if manifest['tracked_dirty']:raise RuntimeError('Commit implementation before evaluation')
    budget=Budget(a.max_calls,a.max_usd,conservative_failures=True);jev=Jev(budget) if 'hybrid' in policies else None
    configs=[{'character':c,'seed':s,'ascension':a.ascension,'policy':policy} for s in a.seeds.split(',') for c in chars for policy in policies]
    with ThreadPoolExecutor(max_workers=a.workers) as pool: results=list(pool.map(lambda c:episode(c,manifest,jev),configs))
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'manifest':manifest,'configuration':vars(a),'results':results,'budget':{'requests':budget.calls,'cost_usd':budget.spent,'unknown':budget.unknown,'estimated_usd':budget.estimated_usd,'uncertain_calls':budget.uncertain_calls}},indent=2)+'\n')
    if any(r['status']=='error' for r in results):raise SystemExit(1)

if __name__=='__main__':main()
