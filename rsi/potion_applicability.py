"""E168 bounded eligibility experiment; visible arithmetic is not an oracle."""
from .numerical import intent_damage


def defer_reason(state,potion,planned_action):
    ident=potion.get('id');p=state.get('player') or {}
    if ident=='BLOCK_POTION':
        # Play the proposed cards first, then re-evaluate from actual state.
        # No credit for hypothetical card block/kills is used to discard a bottle.
        if planned_action.get('action')!='end_turn':return 'finish_cards_before_block'
        gap=sum(intent_damage(e) for e in state.get('enemies',[]))-p.get('block',0)-p.get('end_turn_block',0)
        if gap<=0:return 'no_visible_unblocked_attack'
    if ident=='REGEN_POTION' and p.get('hp',0)>=p.get('max_hp',0):
        return 'no_current_healing_deficit'
    if ident in ('ASHWATER','SNECKO_OIL'):
        return 'unverified_hand_transformation'
    return None
