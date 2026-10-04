#!/usr/bin/env python3
"""Repack historical instructions, then resolve against independent engine states."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.battle_search import finish
from rsi.campaign_teacher import permitted_state
from rsi.checkpoints import file_hash,wire_pairs
from rsi.engine import Headless
from rsi.macro_transaction import Transaction,automatic,card_key,owned_rules,SHOP
from rsi.research_restore import ENGINE_KEYS
from rsi.trace import Trace,digest
from scripts.evaluate_battle_search_e120 import manifest,audit,write


def source_data(record):
    assert audit([record])['pass']
    events=[json.loads(l) for l in (ROOT/record['trace_path']).read_text().splitlines()]
    requests={e['data']['state_hash']:e['data'] for e in events if e['kind']=='campaign_request'}
    responses={e['data']['state_hash']:e['data']['packet'] for e in events if e['kind']=='campaign_response'}
    decisions=[]
    for e in events:
        if e['kind']!='decision':continue
        d=copy.deepcopy(e['data']);h=digest(d['state'])
        if h in requests:
            d['request']=requests[h];d['packet']=responses[h]
        decisions.append(d)
    return decisions


def step_for(entry,d):
    command=d['chosen']['action'];kind=command['action'];index=None
    if kind in SHOP:index=command['args'][('card' if kind=='buy_card' else 'potion')+'_index']
    elif kind=='select_cards':
        indexes=[int(x) for x in command['args']['indices'].split(',')]
        if len(indexes)!=1:raise ValueError('Only single deck references in v1')
        card=next(c for c in d['state']['cards'] if c['index']==indexes[0]);key=card_key(card)
        occurrence=sum(card_key(c)==key for c in d['state']['cards'] if c['index']<indexes[0])
        matches=[i for i,c in enumerate(entry['player']['deck']) if card_key(c)==key]
        if len(matches)<=occurrence:raise ValueError('Card was not visible at transaction entry')
        kind='select_deck_card';index=matches[occurrence]
    elif kind not in ('remove_card','leave_room'):raise ValueError('Unsupported followup')
    rules=d.get('packet',{}).get('potion_reservations')
    return dict(kind=kind,index=index,potion_reservations=rules)


def compile_run(record):
    ds=source_data(record);bundles={};groups=[];tx=None;rules=[];counts=Counter();changed=[]
    saved=[];input_chars=output_chars=0
    for i,d in enumerate(ds):
        state=d['state'];choices=d['candidates'];h=digest(state);selected=None;new_rules=None;owner='recorded_program'
        if tx:
            result=tx.choose(state,choices)
            if result:selected,new_rules=result;owner='transaction'
        if selected is None and not d['combat_active']:
            selected=automatic(state,choices)
            if selected:owner='mechanical_rule'
        if selected is None:
            selected=d['chosen']
            if 'request' in d:
                owner='expert';steps=[]
                for later in ds[i+1:i+6]:
                    if later['combat_active'] or later['state'].get('context')!=state.get('context'):break
                    try:
                        candidate=steps+[step_for(state,later)]
                        Transaction(state,selected,candidate)
                    except (ValueError,KeyError):break
                    steps=candidate
                tx=Transaction(state,selected,steps) if steps else None
                packet=copy.deepcopy(d['packet']);packet['transaction_steps']=steps
                bundles[h]=dict(packet=packet,first=selected,steps=steps)
                groups.append(dict(seq=d['request']['seq'],steps=len(steps),state_hash=h))
                new_rules=packet['potion_reservations']
                # Conservative new request accounting: complete current deck, plus explicit contract.
                request={**d['request'],'state':state,'transaction_contract':'<=5 followups; only entry-visible offers/deck references; unexpected deltas cancel.'}
                input_chars+=len(json.dumps(request,ensure_ascii=False));output_chars+=len(json.dumps(packet,ensure_ascii=False))
        if new_rules is not None:rules=copy.deepcopy(new_rules)
        rules=owned_rules(state,rules)
        if selected['action']!=d['chosen']['action']:changed.append(dict(index=i,reason='action',owner=owner))
        if 'request' in d:
            counts[owner]+=1
            if rules!=d['packet']['potion_reservations']:changed.append(dict(index=i,reason='reservations',owner=owner))
            if owner!='expert':saved.append(dict(seq=d['request']['seq'],phase=state['decision'],owner=owner))
        if d['combat_active']:
            if permitted_state(state,rules)[1]!=d.get('reserved_potion_indexes',[]) and len(choices)>1:
                changed.append(dict(index=i,reason='combat_mask',owner=owner))
        # The next recorded decision can follow read-only get_map; these leave state unchanged.
        if tx and i+1<len(ds):tx.accepted(state,selected,ds[i+1]['state'])
    return dict(case=record['case'],bundles=bundles,groups=groups,counts=dict(counts),changed=changed,saved=saved,
                input_chars=input_chars,output_chars=output_chars,source_requests=sum(counts.values()))


def synthetic(record):
    ds=source_data(record);n=0
    # Exercise actual observable purchase transitions, then perturb independent fields.
    for i,d in enumerate(ds[:-1]):
        if d['state']['decision']=='shop' and d['chosen']['action']['action']=='buy_card':
            before=d['state'];after=ds[i+1]['state']
            if after['decision']!='shop':continue
            plan=[dict(kind='leave_room',index=None,potion_reservations=None)]
            tx=Transaction(before,d['chosen'],plan);tx.accepted(before,d['chosen'],after)
            assert tx.invalid is None,(record['case'],tx.invalid)
            assert tx.choose(after,ds[i+1]['candidates']);n+=1
            mutations=[lambda s:s['player'].__setitem__('gold',s['player']['gold']+1),
                lambda s:s['player']['deck'].pop(),
                lambda s:s['player']['potions'].append(dict(id='UNEXPECTED')),
                lambda s:s['context'].__setitem__('floor',999),
                lambda s:next(c for c in s['cards'] if c.get('is_stocked')).__setitem__('cost',999),
                lambda s:s['cards'].pop()]
            for mutate in mutations:
                bad=copy.deepcopy(after);mutate(bad)
                t=Transaction(before,d['chosen'],plan);t.accepted(before,d['chosen'],bad)
                assert t.invalid is not None;assert t.choose(bad,ds[i+1]['candidates']) is None;n+=1
            stale=copy.deepcopy(after);stale['player']['gold']+=1
            t=Transaction(before,d['chosen'],plan);t.accepted(before,d['chosen'],after)
            assert t.choose(stale,ds[i+1]['candidates']) is None;n+=1
            break
    for d in ds:
        s=d['state']
        if s['decision']=='potion_reward':
            full=copy.deepcopy(s);full['player']['has_open_potion_slots']=False
            assert automatic(full,d['candidates']) is None;n+=1;break
    for d in ds:
        s=d['state']
        if s['decision']=='map_select' and len(s.get('choices',[]))==1 and len(d['candidates'])>1:
            low=copy.deepcopy(s);low['player']['hp']=low['player']['max_hp']*.5
            assert automatic(low,d['candidates']) is None;n+=1;break
    return n


def replay_compiled(record,compiled,v):
    ds=source_data(record);by_hash={digest(d['state']):d for d in ds}
    pairs=wire_pairs((ROOT/record['trace_path']).parent/'wire.jsonl')
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**v,'scope':'E164_protocol_replay','case':record['case'],
        'compiled_hash':digest(compiled['bundles'])})
    r=dict(case=record['case'],status='error',run_id=trace.directory.name,steps=0,requests=0,transaction_actions=0,automatic_actions=0)
    started=time.monotonic();engine=None;state={};tx=None;rules=[]
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        for i,(original,expected) in enumerate(pairs):
            left=120-(time.monotonic()-started)
            if left<=0:raise TimeoutError('Protocol replay cap')
            engine.timeout=min(15,left);command=original;selected=None;new_rules=None;source='recorded_program'
            if original['cmd']=='action':
                d=by_hash[digest(state)];choices=d['candidates']
                if tx:
                    answer=tx.choose(state,choices)
                    if answer:selected,new_rules=answer;source='transaction';r['transaction_actions']+=1
                if selected is None and not d['combat_active']:
                    selected=automatic(state,choices)
                    if selected:source='mechanical_rule';r['automatic_actions']+=1
                if selected is None and digest(state) in compiled['bundles']:
                    b=compiled['bundles'][digest(state)];selected=b['first'];new_rules=b['packet']['potion_reservations']
                    tx=Transaction(state,selected,b['steps']) if b['steps'] else None
                    r['requests']+=1;source='expert'
                if selected is None:
                    if 'request' in d:raise ValueError('Missing compiled expert instruction')
                    selected=d['chosen']
                command=selected['action']
                if command!=original:raise ValueError(f'Action mismatch at {i}')
                if new_rules is not None:rules=copy.deepcopy(new_rules)
                rules=owned_rules(state,rules)
                if 'packet' in d and rules!=d['packet']['potion_reservations']:raise ValueError('Reservation mismatch')
                if d['combat_active'] and len(choices)>1 and permitted_state(state,rules)[1]!=d.get('reserved_potion_indexes',[]):
                    raise ValueError('Combat reservation mask changed')
                trace.write('decision',dict(state_hash=digest(state),source=source,chosen=selected,queue_error=tx.invalid if tx else None))
            before=state;state=engine.send(command);r['steps']+=1
            if digest(state)!=digest(expected):raise ValueError(f'State mismatch at {i}')
            if tx and selected:tx.accepted(before,selected,state)
        r.update(status='match',final_hash=digest(state))
        assert r['requests']==compiled['counts']['expert']
    except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
    finish(trace,r,engine,started);return r


def main(output):
    if output.exists():raise ValueError('Never overwrite evidence')
    started=time.monotonic();v={**manifest(),'experiment':'E164'}
    source=ROOT/'experiments/E160/evaluation-v1.json';e=json.loads(source.read_text())
    assert all(v[k]==e['manifest'][k] for k in ENGINE_KEYS)
    rs=[r for r in e['records'] if r['arm']=='astra_campaign'];compiled=[compile_run(r) for r in rs]
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    for r in compiled:write(directory/(r['case']+'.json'),r)
    checks=sum(synthetic(r) for r in rs)
    with ThreadPoolExecutor(max_workers=4) as pool:
        proofs=list(pool.map(lambda pair:replay_compiled(*pair,v),zip(rs,compiled)))
    baseline=sum(r['source_requests'] for r in compiled);expert=sum(r['counts'].get('expert',0) for r in compiled)
    result=dict(manifest=v,source_sha256=file_hash(source),compiled=compiled,replays=proofs,synthetic_checks=checks,
        baseline_requests=baseline,compiled_requests=expert,saved_requests=baseline-expert,reduction=1-expert/baseline,
        original_input_chars=sum(r['expert_input_chars'] for r in rs),compiled_input_chars=sum(r['input_chars'] for r in compiled),
        original_output_chars=sum(r['expert_output_chars'] for r in rs),compiled_output_chars=sum(r['output_chars'] for r in compiled),
        actual_model_tokens=None,actual_model_cost_usd=None,new_policy_runs=0,
        scope='Offline historical instruction packing and independent engine replay; not measured fresh expert performance')
    result['audit']=audit(proofs);result['seconds']=time.monotonic()-started
    result['passed']=(baseline==200 and result['reduction']>=.3 and not any(r['changed'] for r in compiled)
        and all(r['status']=='match' for r in proofs) and result['audit']['pass'] and result['seconds']<=600)
    write(output,result)
    print(json.dumps({k:result[k] for k in ('passed','baseline_requests','compiled_requests','reduction','seconds','synthetic_checks','audit')}))
    print(json.dumps([dict(case=c['case'],counts=c['counts'],changes=c['changed'],replay=p['status'],error=p.get('error')) for c,p in zip(compiled,proofs)]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
