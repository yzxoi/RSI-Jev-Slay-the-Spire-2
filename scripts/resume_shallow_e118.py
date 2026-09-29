#!/usr/bin/env python3
"""E118 transport-only continuation: retain failed cells, send only unstarted cells."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import benchmark_shallow_e118 as base
from rsi.shallow_bench import CONFIGS, digest, canonical, request_body, reservation

TIMEOUT = 'total_http_deadline_60s'


def transport_error(error):
    return error == TIMEOUT or (isinstance(error,str) and error.startswith(
        ('IncompleteRead:', 'RemoteDisconnected:', 'TimeoutError:')))


def settle_transport(ledger, reserve, row, failures):
    ledger.settle(reserve,row['usage'].get('cost'),row['valid'])
    failures += transport_error(row.get('error'))
    if (ledger.stop == 'unknown_billing' and transport_error(row.get('error')) and failures < 3
            and ledger.consecutive_invalid < 3
            and (ledger.calls < 20 or ledger.invalid/ledger.calls <= .1)):
        ledger.stop = None
    return failures


def settle_timeout(ledger, reserve, row, timeouts):
    ledger.settle(reserve, row['usage'].get('cost'), row['valid'])
    timeouts += row.get('error') == TIMEOUT
    # At most two timed-out cells are tolerated; no retry and no free billing assumption.
    if (ledger.stop == 'unknown_billing' and row.get('error') == TIMEOUT and timeouts < 3
            and ledger.consecutive_invalid < 3
            and (ledger.calls < 20 or ledger.invalid/ledger.calls <= .1)):
        ledger.stop = None
    return timeouts


def read_source(source, config, bank):
    folder = source/config
    top = json.loads((source/'manifest.json').read_text())
    manifest = json.loads((folder/'manifest.json').read_text())
    rows = json.loads((folder/'rows.json').read_text())
    raw = (folder/'trace.jsonl').read_bytes()
    events = [json.loads(x) for x in raw.splitlines()]
    assert top['bank_digest'] == digest(bank)
    assert top['configurations'][config] == CONFIGS[config]
    assert manifest['trace_sha256'] == base.sha_file(folder/'trace.jsonl')
    assert manifest['ledger']['stop'] == 'unknown_billing'
    assert transport_error(events[-1]['reply'].get('error')), 'Only a recognized transport failure can be resumed'
    ledger = base.Ledger(CONFIGS[config]['cap'])
    items = {i['id']:i for i in bank['items']}
    for n in range(0,len(events),2):
        req, res = events[n:n+2]; idx = n//2; cell = bank['schedule'][idx]
        assert req['kind']=='request' and res['kind']=='response'
        assert req['index']==res['index']==idx and req['cell']==res['cell']==cell
        body = request_body(config,items[cell['item_id']],cell['task'])
        assert req['body']==body and rows[idx]['request_sha256']==digest(body)
        assert rows[idx]['response_sha256']==digest(res['reply'])
        assert all(rows[idx][k]==v for k,v in base.score(config,items[cell['item_id']],cell['task'],res['reply']).items())
        reserve = reservation(config,body)
        if ledger.stop:
            # Previously audited continuation boundaries; never replay a failed request.
            assert transport_error(rows[idx-1].get('error'))
            assert sum(transport_error(r.get('error')) for r in rows[:idx]) < 3
            assert ledger.consecutive_invalid < 3 and (ledger.calls < 20 or ledger.invalid/ledger.calls <= .1)
            ledger.stop=None
        assert reserve==req['reservation'] and ledger.acquire(reserve)
        ledger.settle(reserve,rows[idx]['usage'].get('cost'),rows[idx]['valid'])
    assert ledger.as_dict()==manifest['ledger']
    assert len(rows)==104 and all(not r.get('attempted') for r in rows[ledger.calls:])
    assert sum(transport_error(r.get('error')) for r in rows[:ledger.calls]) < 3
    return manifest, rows, raw, ledger


def continue_config(config, bank, source, out, key):
    old, rows, raw, ledger = read_source(source, config, bank)
    initial_calls = ledger.calls
    ledger.stop = None
    failures = sum(transport_error(r.get('error')) for r in rows[:initial_calls])
    tested_sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    folder = out/config; folder.mkdir()
    items = {i['id']:i for i in bank['items']}
    started = time.monotonic()
    with (folder/'trace.jsonl').open('xb') as trace:
        trace.write(raw); trace.flush()
        for idx in range(initial_calls,104):
            cell = bank['schedule'][idx]; item = items[cell['item_id']]; task = cell['task']
            body = request_body(config,item,task); reserve = reservation(config,body)
            if old['elapsed_seconds'] + time.monotonic()-started >= 1500:
                ledger.stop = ledger.stop or 'batch_deadline'
            if not ledger.acquire(reserve):
                rows[idx] = dict(base.score(config,item,task,{'error':'unstarted: '+ledger.stop}),attempted=False)
                continue
            trace.write((canonical(dict(kind='request',index=idx,cell=cell,body=body,reservation=reserve))+'\n').encode())
            trace.flush(); base.os.fsync(trace.fileno())
            start = time.monotonic(); reply = base.post(config,body,key); seconds = time.monotonic()-start
            trace.write((canonical(dict(kind='response',index=idx,cell=cell,seconds=seconds,reply=reply))+'\n').encode())
            trace.flush(); base.os.fsync(trace.fileno())
            row = base.score(config,item,task,reply)
            row.update(attempted=True,seconds=seconds,request_sha256=digest(body),response_sha256=digest(reply))
            rows[idx] = row
            failures = settle_transport(ledger,reserve,row,failures)
            if ledger.calls%8==0 or ledger.stop:
                print(canonical(dict(config=config,completed=ledger.calls,new_calls=ledger.calls-initial_calls,
                    cost=ledger.cost,unknown_reserved=ledger.unknown_reserved,invalid=ledger.invalid,stop=ledger.stop)),flush=True)
    manifest = dict(config=config,ledger=ledger.as_dict(),elapsed_seconds=old['elapsed_seconds']+time.monotonic()-started,
        continuation_elapsed_seconds=time.monotonic()-started,trace_sha256=base.sha_file(folder/'trace.jsonl'),
        initial_calls=initial_calls,source_manifest=old,source_manifest_sha256=base.sha_file(source/config/'manifest.json'),
        tested_sha=tested_sha,policy_version=2,transport_errors=failures,
        timeouts=sum(r.get('error')==TIMEOUT for r in rows if r.get('attempted')))
    base.write_json(folder/'rows.json',rows); base.write_json(folder/'manifest.json',manifest)
    return manifest


def audit_config(config, bank, source, out):
    old, original, raw, ledger = read_source(source,config,bank)
    folder=out/config; final=json.loads((folder/'manifest.json').read_text())
    rows=json.loads((folder/'rows.json').read_text()); trace=(folder/'trace.jsonl').read_bytes()
    assert final['source_manifest']==old and final['initial_calls']==ledger.calls
    assert final['source_manifest_sha256']==base.sha_file(source/config/'manifest.json')
    assert trace.startswith(raw) and final['trace_sha256']==base.sha_file(folder/'trace.jsonl')
    assert rows[:ledger.calls]==original[:ledger.calls], 'Previously attempted cells must remain untouched'
    events=[json.loads(x) for x in trace[len(raw):].splitlines()]
    items={i['id']:i for i in bank['items']}; ledger.stop=None
    policy=final.get('policy_version',1)
    counter=sum((transport_error(r.get('error')) if policy==2 else r.get('error')==TIMEOUT) for r in original[:ledger.calls])
    for n in range(0,len(events),2):
        req,res=events[n:n+2]; idx=final['initial_calls']+n//2; cell=bank['schedule'][idx]
        assert req['kind']=='request' and res['kind']=='response'
        assert req['index']==res['index']==idx and req['cell']==res['cell']==cell
        body=request_body(config,items[cell['item_id']],cell['task']); reserve=reservation(config,body)
        assert req['body']==body and rows[idx]['request_sha256']==digest(body)
        assert rows[idx]['response_sha256']==digest(res['reply'])
        assert all(rows[idx][k]==v for k,v in base.score(config,items[cell['item_id']],cell['task'],res['reply']).items())
        assert reserve==req['reservation'] and ledger.acquire(reserve)
        counter=(settle_transport if policy==2 else settle_timeout)(ledger,reserve,rows[idx],counter)
    assert len(rows)==104 and sum(r.get('attempted',False) for r in rows)==ledger.calls
    assert counter==final['transport_errors' if policy==2 else 'timeouts']
    for k in ('cost','unknown_reserved','invalid','consecutive_invalid','calls','cap'):
        assert ledger.as_dict()[k]==final['ledger'][k]
    assert ledger.cost+ledger.unknown_reserved <= CONFIGS[config]['cap']
    assert all(not r.get('attempted') for r in rows[ledger.calls:])
    return dict(passed=True,total_pairs=ledger.calls,new_pairs=ledger.calls-final['initial_calls'],
        preserved_failed_cells=True,cost=ledger.cost,unknown_reserved=ledger.unknown_reserved)


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('command',choices=('run','audit'))
    p.add_argument('--source',type=Path,default=ROOT/'artifacts/runs/e118-combined-v3')
    p.add_argument('--output',type=Path,default=ROOT/'artifacts/runs/e118-supplement-v4')
    p.add_argument('--configs',nargs='+',default=['deepseek_low','qwen_low','kimi_low'])
    p.add_argument('--env-file',default=str(ROOT/'.env'))
    p.add_argument('--execute',action='store_true')
    a=p.parse_args(); bank=json.loads((ROOT/'experiments/E118/fixtures.json').read_text());base.verify_bank(bank)
    if a.command=='audit':
        top=json.loads((a.output/'manifest.json').read_text())
        assert top['bank_digest']==digest(bank)
        report={c:audit_config(c,bank,a.source,a.output) for c in top['configs']}
        base.write_json(a.output/'audit.json',report);print(json.dumps(report,indent=2));return
    if not a.execute: raise SystemExit('--execute required')
    if set(a.configs)-{'deepseek_low','qwen_low','kimi_low'} or not a.configs or len(set(a.configs))!=len(a.configs):
        raise SystemExit('Only the preregistered stopped configurations may resume')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise SystemExit('Commit tracked changes before evaluation')
    top=json.loads((a.source/'manifest.json').read_text())
    assert top['combined_conservative_ceiling']<=3
    for c in a.configs: read_source(a.source,c,bank)
    a.output.mkdir(parents=True,exist_ok=False)
    manifest=dict(experiment='E118',iteration=4,policy_version=2,tested_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        bank_digest=digest(bank),fixture_sha256=base.sha_file(ROOT/'experiments/E118/fixtures.json'),configs=a.configs,
        source=str(a.source),source_config_tested_shas={c:top['config_tested_shas'][c] for c in a.configs},
        combined_conservative_ceiling=top['combined_conservative_ceiling'],failed_cell_retries=0,
        max_tolerated_transport_failures_per_configuration=2,cumulative_active_deadline_seconds=1500,python=sys.version)
    base.write_json(a.output/'manifest.json',manifest);key=base.read_key(a.env_file)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(a.configs)) as pool:
        fs=[pool.submit(continue_config,c,bank,a.source,a.output,key) for c in a.configs]
        for f in concurrent.futures.as_completed(fs): print(canonical({'done':f.result()}),flush=True)
    report={c:audit_config(c,bank,a.source,a.output) for c in a.configs}
    base.write_json(a.output/'audit.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__': main()
