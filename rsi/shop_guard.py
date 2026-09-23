"""Opt-in funded-shop relic shortlist; legal candidates remain authoritative."""


def funded_relic_candidates(state, candidates, purchases_here, minimum_gold=250):
    scene = state.get('screen', state.get('decision'))
    shop = state.get('shop') or state
    gold = (state.get('run') or {}).get('gold') if scene == 'SHOP' else (state.get('player') or {}).get('gold')
    report = {'triggered': False, 'gold': gold, 'purchases_here': purchases_here,
              'relics': [], 'reason': None}
    if scene not in ('SHOP', 'shop'):
        report['reason'] = 'outside_shop'
    elif shop.get('is_open') is False:
        report['reason'] = 'inventory_closed'
    elif not isinstance(gold, (int, float)) or gold < minimum_gold:
        report['reason'] = 'below_gold_threshold'
    elif purchases_here:
        report['reason'] = 'already_purchased_here'
    else:
        relics = []
        for candidate in candidates:
            if candidate['action']['action'] != 'buy_relic':
                continue
            item = candidate.get('details') or {}
            price = item.get('price', item.get('cost'))
            if not item.get('is_stocked') or not isinstance(price, (int, float)) or price > gold:
                continue
            relics.append(candidate)
        if relics:
            report['triggered'] = True
            report['relics'] = [{'index': (c['action'].get('option_index') if scene == 'SHOP'
                                          else c['action'].get('args', {}).get('relic_index')),
                                 'name': (c.get('details') or {}).get('name'),
                                 'price': (c.get('details') or {}).get('price', (c.get('details') or {}).get('cost'))}
                                for c in relics]
            report['reason'] = 'funded_relic_purchase'
            return relics, report
        report['reason'] = 'no_affordable_relic'
    return candidates, report
