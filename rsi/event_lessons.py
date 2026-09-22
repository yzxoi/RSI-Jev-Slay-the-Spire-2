"""Trace-backed event lessons and exact noncombat arithmetic."""
def context(state):
 if state.get('decision')!='event_choice':return None
 p=state.get('player',{});hp=p.get('hp',0);maximum=p.get('max_hp',hp)
 out={'scope':'Immediate deterministic effects only; combat cost and later outcomes are unknown.','options':[]}
 for o in state.get('options',[]):
  v=o.get('vars') or {};d={'index':o['index']}
  if 'Heal' in v and '{Heal' in (o.get('description') or ''):d['immediate_healing']=min(maximum-hp,v['Heal'])
  if 'HpLoss' in v and '{HpLoss' in (o.get('description') or ''):d['remaining_hp_after_cost']=hp-v['HpLoss']
  if len(d)>1:out['options'].append(d)
 if state.get('event_name')=='Dense Vegetation':
  out['lesson']='Rest includes a mandatory fight. Observed Act1 A10 prefix spawned four Wrigglers and all five starter-heavy characters died. Healing before that fight is not net healing. Trudge On trades a known small HP loss for gold and avoids that fight. Compare capped healing minus plausible combat damage; prefer the known loss when survivable and the deck lacks reliable multi-enemy damage. This is empirical risk evidence, not proof every such fight loses.'
  out['evidence']='E018 full_eval_007 post-hoc diagnostic, version v0.111.0'
 return out if out['options'] or out.get('lesson') else None
