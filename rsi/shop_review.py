"""Rare high-gold shop exit review for the native one-writer controller."""


def funded_shop_exit_review(raw, action, purchases_here=0, explicit_choice=False,
                            minimum_gold=250):
    report = {'review': False, 'reason': None, 'gold': None, 'affordable_relics': []}
    if raw.get('screen') != 'SHOP':
        report['reason'] = 'outside_shop'
        return report
    shop = raw.get('shop') or {}
    if explicit_choice:
        report['reason'] = 'explicit_expert_choice'
    elif action.get('action') not in ('close_shop_inventory', 'proceed'):
        report['reason'] = 'not_exiting'
    elif not shop.get('is_open'):
        report['reason'] = 'inventory_closed'
    else:
        gold = (raw.get('run') or {}).get('gold')
        report['gold'] = gold
        if not isinstance(gold, (int, float)) or gold < minimum_gold:
            report['reason'] = 'below_gold_threshold'
        elif purchases_here or (shop.get('card_removal') or {}).get('used') or any(
                item.get('is_stocked') is False
                for kind in ('cards', 'relics', 'potions') for item in shop.get(kind, [])):
            report['reason'] = 'already_purchased_here'
        else:
            report['affordable_relics'] = [
                {'index': item['index'], 'relic_id': item.get('relic_id'), 'price': item['price']}
                for item in shop.get('relics', [])
                if item.get('is_stocked') and isinstance(item.get('price'), (int, float))
                and item['price'] <= gold and item.get('enough_gold', True)]
            if report['affordable_relics']:
                report['review'] = True
                report['reason'] = 'funded_shop_exit'
            else:
                report['reason'] = 'no_affordable_relic'
    return report
