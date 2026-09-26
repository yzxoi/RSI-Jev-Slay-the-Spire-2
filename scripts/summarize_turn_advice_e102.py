"""Read-only E102 diagnostics; no new model calls or counterfactual outcomes."""
import json

from rsi.engine import ROOT
from rsi.policy import model_state
from rsi.trace import digest


def main():
    directory = ROOT / 'experiments/E102'
    report = json.loads((directory / 'result.json').read_text())
    analyses = []
    for result in report['results']:
        rows = [json.loads(line) for line in (ROOT / result['trace_path']).read_text().splitlines()]
        state = answer = candidates = None
        retained = None
        requests = []
        replies = []
        ledger = []
        endings = []
        openings = []
        seen_rounds = set()
        omission_valid = True
        for row in rows:
            kind, data = row['kind'], row['data']
            if kind == 'before':
                state = data['state']
                answer = None
                turn = state.get('round')
                if state.get('decision') == 'combat_play' and turn not in seen_rounds:
                    seen_rounds.add(turn)
                    openings.append({'round': turn, 'hp': state['player']['hp'],
                                     'leader_hp': next(e['hp'] for e in state['enemies'] if e['name'] == 'Kin Priest')})
            elif kind == 'candidates':
                candidates = data
            elif kind == 'turn_advice_request':
                requests.append(data)
                player = model_state(state)['player']
                static = {key: player.get(key) for key in ('deck', 'relics')}
                if retained is None:
                    retained = static
                else:
                    omission_valid &= retained == static
            elif kind == 'turn_advice_response':
                packet = data['packet']
                replies.append(packet)
                ledger.append({'round': packet['round'], 'commit': data['commit'],
                               'state_hash': packet['state_hash'],
                               'guidance_chars': len(packet['goal']) + len(packet['guidance'])})
            elif kind == 'model_response':
                answer = data['response']['answers']['action']
            elif (kind == 'selected' and data['choice']['action']['action'] == 'end_turn'
                  and state.get('energy', 0) > 0):
                endings.append({'round': state['round'], 'state_hash': digest(state),
                                'hp': state['player']['hp'], 'block': state['player']['block'],
                                'energy': state['energy'], 'player_powers': state.get('player_powers', []),
                                'enemies': [{key: e.get(key) for key in ('index', 'name', 'hp', 'intents')}
                                            for e in state['enemies']],
                                'hand': [{key: c.get(key) for key in ('index', 'name', 'cost', 'stats', 'can_play')}
                                         for c in state['hand']],
                                'candidates': candidates, 'answer': answer})
        input_chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in requests)
        output_chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in replies)
        assert input_chars == result['expert_input_chars']
        assert output_chars == result['expert_output_chars']
        assert len(ledger) == result['expert_packets']
        analyses.append({'run_id': result['run_id'], 'case': result['case'], 'arm': result['arm'],
                         'omitted_deck_relic_text_unchanged': omission_valid,
                         'teacher_ledger': ledger, 'round_openings_before_program_potions': openings,
                         'all_end_turns_with_unspent_energy': endings})
    output = {'scope': 'Post-hoc descriptive trace analysis, not an intervention or counterfactual test.',
              'payload_counts_reconciled': True,
              'all_omitted_text_unchanged': all(a['omitted_deck_relic_text_unchanged'] for a in analyses),
              'runs': analyses}
    (directory / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({key: value for key, value in output.items() if key != 'runs'}, indent=2))


if __name__ == '__main__':
    main()
