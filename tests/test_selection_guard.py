import copy
import json
from pathlib import Path

from rsi.scenes import candidates
from rsi.selection_guard import preserve_exhaust_block


FIXTURE = Path(__file__).resolve().parents[1] / 'experiments/E064/frozen-selection.json'


def frozen():
    return copy.deepcopy(json.loads(FIXTURE.read_text())['raw'])


def test_frozen_native_exhaust_selection_preserves_evil_eye():
    raw = frozen()
    offered = candidates(raw)
    kept, report = preserve_exhaust_block(raw, offered)
    assert report == {'applied': True, 'reason': 'preserve_affordable_conditional_block',
                      'incoming': 31, 'hp': 36, 'block': 0, 'energy': 2,
                      'protected_option_indices': [3], 'protected_block': {3: 18}}
    assert {c['action']['option_index'] for c in kept} == {0, 1, 2}
    assert len(kept) < len(offered)


def test_does_not_filter_other_selection_or_safe_threat():
    for change in ('upgrade', 'no_attack', 'enough_block', 'unaffordable'):
        raw = frozen()
        if change == 'upgrade':
            raw['selection']['prompt'] = '选择一张牌升级'
        elif change == 'no_attack':
            for enemy in raw['combat']['enemies']:
                enemy['intents'] = []
        elif change == 'enough_block':
            raw['combat']['player']['block'] = 31
        else:
            raw['combat']['player']['energy'] = 0
        offered = candidates(raw)
        kept, report = preserve_exhaust_block(raw, offered)
        assert kept == offered, change
        assert not report['applied'], change


def test_never_removes_only_legal_target():
    raw = frozen()
    raw['selection']['cards'] = [raw['selection']['cards'][3]]
    offered = candidates(raw)
    kept, report = preserve_exhaust_block(raw, offered)
    assert kept == offered
    assert not report['applied']
