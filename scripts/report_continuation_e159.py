#!/usr/bin/env python3
"""Read-only E159 trace diagnosis; distinguish combat skill from changed encounters."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsi.checkpoints import wire_pairs
from rsi.trace import digest
from scripts.pilot_continuation_e159 import ARMS
from scripts.pilot_root_teacher_e149 import info
from scripts.evaluate_battle_search_e120 import audit, manifest, write


def first_entry(record):
    pairs=wire_pairs((ROOT/record['trace_path']).with_name('wire.jsonl'))
    start=record['restore_commands']-1
    local=record['first_fight']
    state=pairs[start+local['steps']][1]
    if digest(state)!=local['final_hash']:
        raise ValueError('First-fight endpoint no longer matches raw wire')
    prefix=[dict(before=digest(pairs[i][1]),action=pairs[i+1][0],after=digest(pairs[i+1][1]))
            for i in range(start,start+local['steps'])]
    if digest(prefix)!=local['transition_hash']:
        raise ValueError('First-fight transition measurement differs from raw wire')
    for _,state in pairs[start:]:
        if state['decision']=='combat_play':
            p=state['player'];c=state.get('context') or {}
            return dict(state_hash=digest(state),room_type=c.get('room_type'),act=c.get('act'),floor=c.get('floor'),
                enemies=[e.get('id',e.get('name')) for e in state.get('enemies',[])],
                hp=p.get('hp'),max_hp=p.get('max_hp'),deck_hash=digest(p.get('deck')),
                potions=[v.get('id',v.get('name')) for v in p.get('potions',[])])
    return None


def report(source, output, figures):
    data=json.loads(source.read_text());proof=audit(data)
    if not proof['pass'] or not data['summary']['complete']:raise ValueError('Cannot present an incomplete paired cohort')
    old=json.loads((ROOT/'experiments/E149/analysis-v3.json').read_text())
    all_loss={r['case'] for r in old['rows'] if r['all_discovery_defeats']}
    rows=[]
    for r in data['records']:
        entries={a:first_entry(r['arms'][a]) for a in ARMS}
        actor,program=(r['arms'][a]['first_fight'] for a in ('actor_actor','actor_program'))
        changed=any(entries['actor_actor'][k]!=entries['actor_program'][k] for k in ('act','floor','room_type','enemies'))
        rows.append({k:r[k] for k in ('case','seed','ascension','mode')} | dict(entries=entries,
            local={a:r['arms'][a]['first_fight'] for a in ARMS},
            act2={a:2 in r['arms'][a]['acts_seen'] for a in ARMS},
            final_context={a:r['arms'][a].get('final_context') for a in ARMS},
            encounter_changed=changed,previous_all_discovery_losses=r['case'] in all_loss,
            rescued=actor['status']=='defeat' and program['status']=='clear',
            lost=actor['status']=='clear' and program['status']=='defeat'))
    out=dict(manifest=manifest(),source=info(source),prior=info(ROOT/'experiments/E149/analysis-v3.json'),
        tested_sha=data['manifest']['code_commit'],summary=data['summary'],audit=proof,
        seconds=data['seconds'],cpu_seconds=data['cpu_seconds'],rows=rows,
        first_fight_wire_checks=120,
        rescued=sum(r['rescued'] for r in rows),lost=sum(r['lost'] for r in rows),
        rescued_previous_all_loss=sum(r['rescued'] and r['previous_all_discovery_losses'] for r in rows),
        changed_encounters=[r['case'] for r in rows if r['encounter_changed']],
        counts_by_mode={m:{a:sum(r['local'][a]['status']=='clear' for r in rows if r['mode']==m) for a in ARMS}
                        for m in ('combat','prepare')},
        counts_by_ascension={str(n):{a:sum(r['local'][a]['status']=='clear' for r in rows if r['ascension']==n) for a in ARMS}
                             for n in (0,5,10)})
    write(output,out)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    colors=['#4477aa','#80b1d3','#ee9944','#cc6677']
    labels=['Actor / Actor','Search / Actor','Actor / Program','Search / Program']
    axes[0].barh(labels,[data['summary']['counts'][a]['first_clears'] for a in ARMS],color=colors)
    axes[0].set(title='First action / continuation',xlabel='First fights cleared (of 30)',xlim=(0,30))
    for i,m in enumerate(('combat','prepare')):
        for j,a in enumerate(('actor_actor','actor_program')):
            axes[1].bar(i+(j-.5)*.3,out['counts_by_mode'][m][a],width=.28,color=colors[j*2],
                        label=['Actor continuation','Program continuation'][j] if i==0 else None)
    axes[1].set(xticks=[0,1],xticklabels=['Combat root','Preparation root'],ylabel='First fights cleared (of 15)',
                ylim=(0,15),title='Same actor first action')
    axes[1].legend(fontsize=8)
    sr=data['summary']['rows'];seeds=list(dict.fromkeys(r['seed'] for r in sr))
    gains=[np.mean([r['continuation_delta'] for r in sr if r['seed']==s]) for s in seeds]
    axes[2].bar(range(15),gains,color=['#4477aa']*5+['#ee9944']*5+['#cc6677']*5)
    axes[2].set(xticks=[2,7,12],xticklabels=['A0 (5 seeds)','A5 (5 seeds)','A10 (5 seeds)'],
                ylabel='Mean paired utility gain',title='Each bar: one game-seed cluster')
    axes[2].axhline(0,color='grey',linewidth=.6)
    fig.suptitle('E159: continuation matters locally; 120 conditional full suffixes, zero full-run victories')
    figures.mkdir(parents=True,exist_ok=True)
    for ext in ('png','svg'):fig.savefig(figures/('continuation-diagnosis.'+ext),dpi=160)
    plt.close(fig)
    print(json.dumps({k:out[k] for k in ('rescued','lost','rescued_previous_all_loss','changed_encounters','first_fight_wire_checks','audit')}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('source','output','figures'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Never overwrite prior diagnosis')
    report(a.source.resolve(),a.output,a.figures)
