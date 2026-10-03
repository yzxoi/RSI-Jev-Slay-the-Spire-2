#!/usr/bin/env python3
"""Post-gate, read-only TRAIN/DEV overfitting and task-input sensitivity diagnosis."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from rsi.task_value import Critic,metrics,PHASES,ridge_features
from rsi.checkpoints import file_hash
from scripts.probe_task_value_e148 import checked,load_data
from scripts.pilot_fullpolicy_e140 import load_phase
from scripts.evaluate_battle_search_e120 import manifest,write


def main(output):
    start=time.monotonic();torch.set_num_threads(1)
    bank=checked(ROOT/'experiments/E148/bank-v2.json');training=checked(ROOT/'experiments/E148/training-v1.json')
    data=load_data(bank);actor=load_phase(bank['behavior']);all_results={}
    for split in ('train','dev'):
        ids=[i for i,r in enumerate(bank['records']) if r['split']==split]
        mask=np.isin(data['case_ids'],ids);d={k:v[mask] for k,v in data.items()}
        x=np.concatenate([d['states'],d['tasks']],1);zero=x.copy();zero[:,-5:]=0
        preds={'constant':np.full(len(x),training['baselines']['constant']),
               'progress_ridge':ridge_features(d['states'],d['tasks'],d['phases'])@training['baselines']['ridge']}
        changes={}
        for cp in training['models']:
            path=ROOT/cp['path']
            if file_hash(path)!=cp['sha256']:raise ValueError('Changed frozen model')
            m=Critic(actor);m.load_state_dict(torch.load(path,map_location='cpu',weights_only=True)['model']);m.eval()
            key=f"{cp['learner']}-{cp['arm']}"
            with torch.inference_mode():
                preds[key]=m(torch.from_numpy(x if cp['arm']=='task' else zero)).numpy()
                if cp['arm']=='task':
                    shifted=preds[key]-m(torch.from_numpy(zero)).numpy();g=d['tasks'][:,2]==1
                    changes[key]=dict(mean_absolute_prediction_change=float(np.mean(abs(shifted))),
                        post_clear_mean_change=float(shifted[g].mean()) if g.any() else None,
                        caution='Zeroing task context is out-of-distribution for this trained arm; sensitivity only, not an intervention on game returns.')
        groups={'all':np.ones(len(x),dtype=bool),'already_six':d['tasks'][:,2]==1}
        groups.update({f'phase:{p}':d['phases']==j for j,p in enumerate(PHASES)})
        all_results[split]=dict(metrics={key:{g:metrics(p[mask],d['targets'][mask],d['case_ids'][mask]) for g,mask in groups.items()} for key,p in preds.items()},
            task_sensitivity=changes,by_ascension={str(a):{'paths':len(rs),'clear':sum(r['status']=='curriculum_clear' for r in rs)} for a in (0,5,10) for rs in [[r for r in bank['records'] if r['split']==split and r['ascension']==a]]})
    write(output,dict(manifest={**manifest(),'experiment':'E148','scope':'post_gate_read_only_diagnosis'},
        bank_sha256=file_hash(ROOT/'experiments/E148/bank-v2.json'),training_sha256=file_hash(ROOT/'experiments/E148/training-v1.json'),
        results=all_results,seconds=time.monotonic()-start,new_game_actions=0,gradient_updates=0,
        note='Descriptive diagnosis after the preregistered gate failed. No new checkpoint selection, inference about causal game improvement or gate changes.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve prior diagnosis')
    main(a.output)
