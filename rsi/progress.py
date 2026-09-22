"""Order full-run results without assuming equal act lengths."""
from collections import Counter, defaultdict

def progress(result):
    return (result.get('status') == 'victory', result.get('act') or 0, result.get('floor') or 0)

def compare(results, baseline, treatment):
    pairs=defaultdict(dict)
    for r in results:
        if r['policy'] in (baseline,treatment):
            key=(r['character'],r['seed'],r.get('ascension'))
            if r['policy'] in pairs[key]:raise ValueError('Duplicate run in paired comparison')
            pairs[key][r['policy']]=r
    outcomes=Counter();details=[]
    for key,p in pairs.items():
        if len(p)!=2 or any(r['status'] not in ['victory','normal_defeat'] for r in p.values()):
            outcomes['incomplete_or_error']+=1;continue
        a,b=progress(p[baseline]),progress(p[treatment]);label='better' if b>a else 'worse' if b<a else 'tie'
        outcomes[label]+=1;details.append({'character':key[0],'seed':key[1],'baseline':a,'treatment':b,'outcome':label})
    return {'baseline':baseline,'treatment':treatment,'outcomes':dict(outcomes),'pairs':details}
