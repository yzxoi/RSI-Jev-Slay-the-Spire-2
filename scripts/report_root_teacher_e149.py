#!/usr/bin/env python3
"""Read-only diagnosis of the frozen E149 teacher pilot, including censored cases."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rsi.checkpoints import file_hash
from rsi.root_teacher import utility
from scripts.evaluate_battle_search_e120 import audit, manifest, write


def report(source, output, figures, previous=None):
    data = json.loads(source.read_text())
    records = data['records']
    rows, paths = [], []
    for r in records:
        discovery = r.get('discovery', [])
        finished = [xs for xs in discovery if len(xs) == 4]
        for xs in discovery:
            paths.extend(xs)
        for xs in r.get('validation', {}).values():
            paths.extend(xs)
        for name in ('greedy', 'full'):
            paths.extend(r.get(name, {}).values())
        if r.get('failed_probe'):
            paths.append(r['failed_probe'])
        row = {k: r.get(k) for k in ('case', 'seed', 'ascension', 'mode', 'status', 'selected_index',
               'validation_delta', 'selection_optimism', 'search_seconds', 'error')}
        row.update(discovery_complete='selected_index' in r,
            all_discovery_defeats=bool(finished) and 'selected_index' in r and
                all(p['status'] == 'defeat' for xs in discovery for p in xs),
            discovery_clears=sum(p['status'] == 'clear' for xs in discovery for p in xs),
            discovery_paths=sum(len(xs) for xs in discovery))
        rows.append(row)
    complete = [r for r in records if r['status'] == 'complete']
    proof = audit(data)
    out = dict(manifest={**manifest(), 'experiment': 'E149-read-only-report'},
        source=dict(path=str(source.relative_to(ROOT)), sha256=file_hash(source)),
        tested_code=data['manifest']['code_commit'], formal_summary=data['summary'], audit=proof,
        rows=rows, collected_paths=len(paths), path_statuses=dict(Counter(x['status'] for x in paths)),
        discovery_complete=sum(x['discovery_complete'] for x in rows),
        all_loss_roots=sum(x['all_discovery_defeats'] for x in rows),
        all_loss_by_mode={m:sum(x['all_discovery_defeats'] for x in rows if x['mode']==m) for m in ('combat','prepare')},
        complete_roots=len(complete), changed_actions=sum(r.get('selected_index',0)!=0 for r in records),
        seconds=data['seconds'], cpu_seconds=data['cpu_seconds'],
        summed_path_seconds=sum(p['seconds'] for p in paths),
        restore_seconds=sum(p.get('restore_seconds',0) for p in paths),
        continuation_actions=sum(p['steps'] for p in paths),
        restored_commands=sum(p.get('restore_commands',0) for p in paths))
    if complete:
        out['complete_only_diagnostic'] = dict(not_a_replacement_for_formal_gate=True,
            validation_delta=float(np.mean([r['validation_delta'] for r in complete])),
            greedy_clear={arm:sum(r['greedy'][arm]['status']=='clear' for r in complete) for arm in ('actor','selected')},
            full_act2={arm:sum(2 in r['full'][arm]['acts_seen'] for r in complete) for arm in ('actor','selected')},
            validation_clear={arm:sum(p['status']=='clear' for r in complete for p in r['validation'][arm]) for arm in ('actor','selected')},
            actual_validation_rooms={arm:dict(Counter(p['actual_room_type'] for r in complete for p in r['validation'][arm])) for arm in ('actor','selected')})
    if previous is not None:
        old=json.loads(previous.read_text());before={}
        for row in old['records']:
            ps=[p for xs in row.get('discovery',[]) for p in xs]
            ps += [p for xs in row.get('validation',{}).values() for p in xs]
            ps += [p for name in ('greedy','full') for p in row.get(name,{}).values()]
            before.update({(p['case'],p['label']):p for p in ps if p['status'] in ('clear','defeat','victory')})
        compared=0;differences=[]
        for path in paths:
            old_path=before.get((path['case'],path['label']))
            if old_path and path['status'] in ('clear','defeat','victory'):
                compared+=1
                keys=('status','steps','transition_hash','final_hash')
                if any(path.get(k)!=old_path.get(k) for k in keys):
                    differences.append(dict(case=path['case'],label=path['label'],
                        before={k:old_path.get(k) for k in keys},after={k:path.get(k) for k in keys}))
        out['scheduling_parity']=dict(previous_sha256=file_hash(previous),compared_terminal_paths=compared,
            differences=differences,passed=compared>0 and not differences,
            note='Failed/incomplete v1 paths remain incomplete; repeated terminal paths are duplicate compute.')
    write(output,out)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(13,3.8),constrained_layout=True)
    labels=['Combat','Preparation']
    axes[0].bar(labels,[out['all_loss_by_mode'][m] for m in ('combat','prepare')],color=['#4477aa','#ee9944'])
    axes[0].set(title='Roots with every discovery rollout losing',ylabel='Roots (15 planned per mode)',ylim=(0,16))
    for mode,color in [('combat','#4477aa'),('prepare','#ee9944')]:
        rs=[r for r in complete if r['mode']==mode]
        axes[1].scatter([r['discovery_stats'][r['selected_index']]['mean']-r['discovery_stats'][0]['mean'] for r in rs],
            [r['validation_delta'] for r in rs],label=mode,color=color,alpha=.65)
    axes[1].axhline(0,color='grey',linewidth=.7)
    axes[1].set(title=f'Independent validation ({len(complete)}/30 complete)',xlabel='Discovery mean gain',ylabel='Held-out stream mean gain')
    axes[1].legend()
    times=[r['search_seconds'] for r in records if 'search_seconds' in r]
    axes[2].scatter(range(len(times)),times,color='#4477aa',s=18)
    axes[2].axhline(60,color='#bb4444',linestyle='--',label='60s p95 gate')
    axes[2].set(title='Serial discovery cost, including restore',xlabel='Completed discovery root',ylabel='Seconds')
    axes[2].legend()
    fig.suptitle('E149: conditional TRAIN-root teacher pilot; no network training or independent full-run wins')
    for extension in ('png','svg'):
        fig.savefig(figures/('teacher-diagnosis.'+extension),dpi=160)
    plt.close(fig)
    print(json.dumps({k:out[k] for k in ('complete_roots','all_loss_roots','all_loss_by_mode','changed_actions','seconds','cpu_seconds','path_statuses','audit')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--figures',type=Path,required=True)
    p.add_argument('--previous',type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous analysis')
    report(a.source.resolve(),a.output,a.figures,a.previous)
