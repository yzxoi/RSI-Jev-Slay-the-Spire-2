"""Explicit, entry-bound potion obligations; no inferred resource strategy."""
from .trace import digest


def identity(potion):
    return {k: potion.get(k) for k in ('name', 'target_type', 'vars')}


class PotionContract:
    def __init__(self, entry, specification):
        if specification['entry_hash'] != digest(entry):
            raise ValueError('Potion contract entry mismatch')
        self.context = entry['context']
        self.rules = specification['rules']
        self.done = set()
        if len({r['id'] for r in self.rules}) != len(self.rules):
            raise ValueError('Duplicate obligation ID')
        for rule in self.rules:
            self.find(entry, rule)

    def find(self, state, rule):
        matches = [p for p in state['player'].get('potions', []) if identity(p) == rule['potion']]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous contracted potion: '+rule['id'])
        return matches[0]

    def due(self, state, rule):
        when = rule['when']
        if when == 'opening': return True
        if when == 'full_heal_deficit':
            p = state['player']
            healing = int(p['max_hp'] * rule['potion']['vars']['HealPercent'] / 100)
            return p['max_hp'] - p['hp'] >= healing
        raise ValueError('Unknown contract predicate')

    def prepare(self, state, choices):
        if state.get('context') != self.context:
            raise ValueError('Potion contract expired')
        if state['decision'] != 'combat_play':
            return None, choices, {'pending_selection': True}
        reserved = []
        for rule in self.rules:
            if rule['id'] in self.done: continue
            potion = self.find(state, rule)
            candidates = [c for c in choices if c['action']['action'] == 'use_potion'
                          and c['action']['args'].get('potion_index') == potion['index']]
            reserved.extend(c['id'] for c in candidates)
            if not self.due(state, rule): continue
            if rule.get('target'):
                targets = [e for e in state.get('enemies', []) if e['name'] == rule['target']]
                if len(targets) != 1: raise ValueError('Ambiguous contract target')
                candidates = [c for c in candidates if c['action']['args'].get('target_index') == targets[0]['index']]
            else:
                candidates = [c for c in candidates if 'target_index' not in c['action']['args']]
            if len(candidates) != 1: raise ValueError('Due potion is not uniquely legal')
            return candidates[0], choices, {'rule_id':rule['id'], 'predicate':rule['when'], 'state_hash':digest(state)}
        return None, [c for c in choices if c['id'] not in reserved], {'reserved_ids':reserved}

    def accepted(self, rule_id, before, after):
        rule = next(r for r in self.rules if r['id'] == rule_id)
        if rule_id in self.done: raise ValueError('Repeated obligation')
        before_count = sum(identity(p)==rule['potion'] for p in before['player']['potions'])
        after_count = sum(identity(p)==rule['potion'] for p in after['player']['potions'])
        if before_count - after_count != 1: raise ValueError('Potion delivery not confirmed')
        self.done.add(rule_id)
