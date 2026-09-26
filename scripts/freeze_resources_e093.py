"""Extract fixed, natural prefixes; never run the game while choosing fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
from rsi.engine import ROOT, CHARACTERS


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads((args.source_root/'experiments/E089/result.json').read_text())
    cases=[]; reward_kinds=set()
    runs=sorted((r for r in report['results'] if r['policy']=='retaliate'),
                key=lambda r:(r['seed'],CHARACTERS.index(r['character'])))
    for run in runs:
        data=(args.source_root/run['trace_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==run['trace_sha256']
        rows=[json.loads(line) for line in data.splitlines()]
        prefix=[];before=None;selected=None;taken=False
        def case(kind,commands,state_hash):
            return {'kind':kind,'character':run['character'],'seed':run['seed'],
                    'ascension':run['ascension'],'source_trace_sha256':run['trace_sha256'],
                    'prefix_actions':list(commands),'legacy_state_hash':state_hash}
        for row in rows:
            k,d=row['kind'],row['data']
            if k=='before':
                before=d;state=d['state'];potions=state.get('player',{}).get('potions',[])
                if (run['seed']=='e089_holdout_001' and not taken
                        and state['decision']=='combat_play' and potions):
                    cases.append(case('combat',prefix,d['state_hash']));taken=True
            elif k=='selected':selected=d['action']
            elif k=='after' and selected and before:
                after=d['state'];bs=before['state']
                if bs['decision']=='combat_play' and after['decision']=='card_reward':
                    bp=bs['player']['potions'];ap=after['player']['potions']
                    kind='reward_space' if len(ap)>len(bp) else 'reward_full' if len(bp)==2 else None
                    if kind and kind not in reward_kinds:
                        item=case(kind,prefix,before['state_hash']);item.update(trigger_action=selected,
                            legacy_after_hash=d['state_hash'],legacy_reward_inventory=ap)
                        cases.append(item);reward_kinds.add(kind)
                prefix.append(selected);selected=None
    for char in ('ironclad','silent'):
        f=json.loads((ROOT/f'experiments/E067/{char}-floor14-prefix.json').read_text())
        cases.append({'kind':'shop','character':f['character'],'seed':f['seed'],'ascension':f['ascension'],
                      'prefix_actions':f['prefix_actions'],'legacy_state_hash':f['pre_purchase_state_hash'],
                      'source_trace_sha256':f['source_trace_sha256']})
    (ROOT/'experiments/E093/fixtures.json').write_text(json.dumps({'schema_version':1,'cases':cases},indent=2)+'\n')
    print([(c['kind'],c['character'],len(c['prefix_actions'])) for c in cases])


if __name__=='__main__':main()
