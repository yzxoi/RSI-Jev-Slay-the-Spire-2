"""One-turn permission to skip repeated *current HP* review after an accepted expert opener.

This is not permission to ignore candidate filters, projected-loss alerts or
end-turn safety checks. Every accepted transition advances the expected native
state fingerprint; any other change fails closed.
"""

from dataclasses import dataclass

from .status_guard import beckon_endturn_projection


def _scope(state):
    return (state.get('run_id'), (state.get('run') or {}).get('floor'), state.get('turn'))


def _in_combat_turn(state):
    return state.get('screen') == 'COMBAT' or (
        state.get('screen') == 'CARD_SELECTION' and state.get('in_combat'))


@dataclass
class ReviewLease:
    run_id: str
    floor: int
    turn: int
    opening_hash: str
    expected_hash: str
    suppressed_pauses: int = 0
    revoked_reason: str | None = None

    @classmethod
    def accepted_opener(cls, before, after, opening_hash, after_hash):
        """Create only after the state-bound expert action was accepted."""
        if before.get('screen') != 'COMBAT' or before.get('selection'):
            return None
        key = _scope(before)
        if (not all(key) or key != _scope(after) or not _in_combat_turn(after)
                or not opening_hash or not after_hash):
            return None
        lease = cls(*key, opening_hash, after_hash)
        lease.validate(after, after_hash)
        return lease if lease.revoked_reason is None else None

    def revoke(self, reason):
        if self.revoked_reason is None:
            self.revoked_reason = reason
        return False

    def validate(self, state, observed_hash):
        if self.revoked_reason is not None:
            return False
        if _scope(state) != (self.run_id, self.floor, self.turn):
            return self.revoke('scope_changed')
        if not _in_combat_turn(state):
            return self.revoke('scene_changed')
        if observed_hash != self.expected_hash:
            return self.revoke('unexpected_state_change')
        if state.get('screen') == 'CARD_SELECTION':
            return True
        combat = state.get('combat') or {}; player = combat.get('player') or {}
        hp = player.get('current_hp')
        if not isinstance(hp, int) or hp <= 0 or hp != (state.get('run') or {}).get('current_hp'):
            return self.revoke('hp_mismatch')
        for enemy in combat.get('enemies', []):
            if not enemy.get('is_alive'):
                continue
            for intent in enemy.get('intents', []):
                if intent.get('intent_type') == 'Attack':
                    total = intent.get('total_damage')
                    if not isinstance(total, int) or total < 0:
                        return self.revoke('unmodelled_attack')
        beckon = beckon_endturn_projection(state)
        if beckon and (not beckon['known'] or beckon['projected_loss'] >= hp):
            return self.revoke('unsafe_beckon_loss')
        return True

    def accepted_transition(self, state, after_hash):
        """Advance only from a controller-accepted action, not an ambient state change."""
        if self.revoked_reason is not None:
            return False
        if _scope(state) != (self.run_id, self.floor, self.turn):
            return self.revoke('scope_changed')
        if not _in_combat_turn(state):
            return self.revoke('scene_changed')
        self.expected_hash = after_hash
        return self.validate(state, after_hash)

    def suppress_current_hp_pause(self):
        if self.revoked_reason is not None:
            return False
        self.suppressed_pauses += 1
        return True


def current_hp_review(state, danger_hp):
    """The original low-HP gate, factored out for frozen-state replay."""
    return (state.get('screen') == 'COMBAT' and not state.get('selection')
            and (state.get('combat') or {}).get('player', {}).get('energy', 0) > 0
            and (state.get('run') or {}).get('current_hp', 100) <= danger_hp)
