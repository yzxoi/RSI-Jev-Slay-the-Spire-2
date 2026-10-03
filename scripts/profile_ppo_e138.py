#!/usr/bin/env python3
"""E138 auditable, synchronized MPS/CPU microbenchmark; no policy promotion."""
import argparse
import copy
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from rsi.checkpoints import file_hash
from rsi.ppo import ActorCritic, encode, padded
from rsi.ppo_actions import ACTION_LIMIT
from rsi.ppo_data import decisions
from scripts.evaluate_battle_search_e120 import manifest, write


def main(output):
    if output.exists():
        raise ValueError('Preserve previous profiling')
    if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1':
        raise ValueError('Silent MPS fallback must be disabled')
    torch.set_num_threads(1)
    start = time.monotonic()
    v = {**manifest(), 'experiment': 'E138', 'torch': str(torch.__version__),
         'mps_available': torch.backends.mps.is_available(), 'cpu_threads': 1,
         'hardware': subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip()}
    source = ROOT/'experiments/E133/training-v2.json'
    bank = json.loads((ROOT/'experiments/E133/fixtures-v2.json').read_text())
    fixtures = {f['case']: f for f in bank['fixtures']}
    training = json.loads(source.read_text())
    records = [e for row in training['learners'] for e in row['updates'][0]['episodes'][:12]]
    samples = [d for r in records for d in decisions(r, fixtures[r['case']]['previous'])]
    clock = time.monotonic()
    observations = [encode(d['state'], d['choices'], d['previous'], max_actions=ACTION_LIMIT) for d in samples]
    encoding = time.monotonic()-clock
    cp = training['learners'][0]['long_selected']
    if file_hash(ROOT/cp['path']) != cp['sha256']:
        raise ValueError('Changed frozen model')
    saved = torch.load(ROOT/cp['path'], map_location='cpu', weights_only=True)
    model = ActorCritic(**saved['config']); model.load_state_dict(saved['model']); model.eval()
    report = dict(manifest=v, source_sha256=file_hash(source), checkpoint=cp,
                  episodes=24, observations=len(observations), encode_seconds=encoding,
                  input_traces=[{k:r[k] for k in ('case','trace_path','trace_sha256','wire.jsonl_sha256')} for r in records],
                  measurements=[], notes=['Batches repeat fixed real observations; not an engine throughput benchmark.',
                  'All transfers/padding and synchronized output copies included; update uses synthetic targets, never saves weights.'])
    base = padded(observations[:min(128,len(observations))])
    with torch.inference_mode():
        ref, rv = model(*base); rp = ref.probs
    for device in ('cpu', 'mps'):
        if device == 'mps' and not v['mps_available']:
            report['measurements'].append(dict(device=device,status='unavailable')); continue
        try:
            m = copy.deepcopy(model).to(device)
            def sync():
                if device == 'mps': torch.mps.synchronize()
            with torch.inference_mode():
                pred, val = m(*(x.to(device) for x in base))
                prob, val = pred.probs.cpu(), val.cpu(); sync()
            parity = bool(torch.allclose(prob,rp,atol=2e-4,rtol=2e-4) and torch.allclose(val,rv,atol=2e-3,rtol=2e-3))
            report.setdefault('numeric',{})[device] = dict(passed=parity,
                max_probability_error=float((prob-rp).abs().max()),max_value_error=float((val-rv).abs().max()))
            for batch in (1,8,32,128,512):
                obs=[observations[i%len(observations)] for i in range(batch)]
                def forward():
                    with torch.inference_mode():
                        dist, value = m(*(x.to(device) for x in padded(obs)))
                        probs=dist.probs.cpu().numpy(); values=value.cpu().numpy()
                    sync()
                    if not np.isfinite(probs).all() or not np.isfinite(values).all(): raise ValueError('Nonfinite output')
                for _ in range(5): forward()
                times=[]; train=[]
                for rep in range(3):
                    if time.monotonic()-start>600:raise TimeoutError('Profile phase cap')
                    t=time.monotonic()
                    for _ in range(30):forward()
                    times.append((time.monotonic()-t)/30)
                    learner=copy.deepcopy(model).to(device);opt=torch.optim.Adam(learner.parameters(),lr=3e-4)
                    def step():
                        dist, value = learner(*(x.to(device) for x in padded(obs)))
                        selected=torch.zeros(batch,dtype=torch.long,device=device)
                        loss=-dist.log_prob(selected).mean()+.25*value.square().mean()-.01*dist.entropy().mean()
                        opt.zero_grad();loss.backward()
                        torch.nn.utils.clip_grad_norm_(learner.parameters(),.5,error_if_nonfinite=True)
                        opt.step(); sync()
                        if not torch.isfinite(loss).item():raise ValueError('Nonfinite training loss')
                    for _ in range(5):step()
                    t=time.monotonic()
                    for _ in range(10):step()
                    train.append((time.monotonic()-t)/10)
                r=dict(device=device,batch=batch,status='ok',numeric_pass=parity,forward_seconds=times,
                       update_seconds=train,median_forward_seconds=statistics.median(times),median_update_seconds=statistics.median(train))
                report['measurements'].append(r);print(json.dumps(r),flush=True)
        except Exception as exc:
            report['measurements'].append(dict(device=device,status='error',error=f'{type(exc).__name__}: {exc}'))
    both={d:{r['batch']:r for r in report['measurements'] if r.get('status')=='ok' and r['device']==d} for d in ('cpu','mps')}
    report['speedups']={str(b):{k:both['cpu'][b]['median_'+k+'_seconds']/both['mps'][b]['median_'+k+'_seconds'] for k in ('forward','update')} for b in both['cpu'].keys() & both['mps'].keys()}
    analysis=json.loads((ROOT/'experiments/E133/analysis-v1.json').read_text())
    fraction=analysis['total_optimizer_seconds']/analysis['total_training_validation_seconds']
    report['optimizer_fraction']=fraction;report['infinite_optimizer_speedup_upper_bound']=1/(1-fraction)
    report['promote_single_inference']=bool(report.get('numeric',{}).get('mps',{}).get('passed') and report['speedups'].get('1',{}).get('forward',0)>=1.2)
    report['seconds']=time.monotonic()-start
    write(output,report)
    print(json.dumps({k:report[k] for k in ('speedups','optimizer_fraction','infinite_optimizer_speedup_upper_bound','promote_single_inference','seconds')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
