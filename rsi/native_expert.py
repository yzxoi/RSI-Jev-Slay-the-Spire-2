"""Task-mediated, precommitted Astra macro decisions for one live native writer."""
import json
from pathlib import Path
import time

from .scenes import fingerprint
from scripts.evaluate_routing_e099 import committed_response


class NativeExpert:
    def __init__(self, directory, trace, deadline, stop_file=None):
        self.directory = Path(directory).resolve()
        self.trace = trace
        self.deadline = deadline
        self.stop_file = stop_file
        self.count = 0
        self.plan = ''

    def choose(self, raw, choices):
        self.count += 1
        if self.count > 160:
            raise TimeoutError('Native Astra packet cap')
        path = self.directory / f'{self.trace.directory.name}-{self.count:03}.json'
        pending = self.trace.directory / 'pending-expert.json'
        request = dict(seq=self.count, state_hash=fingerprint(raw), state=raw, choices=choices,
            previous_plan=self.plan, response_path=str(path),
            contract='Return state_hash, action, reason, campaign_plan. Macro ownership only; legal native action, current indices. Commit the packet before execution. Plan is supplied to subsequent Jev potion/selection decisions; program plays remain unchanged.')
        self.trace.write('before', dict(state=raw, state_hash=fingerprint(raw)))
        self.trace.write('candidates', choices)
        self.trace.write('expert_required', dict(reason='macro_review', state_hash=fingerprint(raw)))
        pending.write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(waiting='Astra', seq=self.count, screen=raw['screen'],
            floor=(raw.get('run') or {}).get('floor'), pending=str(pending)), ensure_ascii=False), flush=True)
        until = min(self.deadline, time.monotonic() + 600)
        while time.monotonic() < until:
            if self.stop_file and Path(self.stop_file).exists():
                raise RuntimeError('User requested stop while awaiting Astra')
            response = committed_response(path)
            if response:
                packet, commit = response
                if set(packet) != {'state_hash', 'action', 'reason', 'campaign_plan'}:
                    raise ValueError('Invalid native macro packet fields')
                if packet['state_hash'] != fingerprint(raw) or packet['action'] not in [c['action'] for c in choices]:
                    raise ValueError('Stale or illegal native macro packet')
                if not isinstance(packet['campaign_plan'], str) or len(packet['campaign_plan']) > 2000:
                    raise ValueError('Invalid native campaign plan')
                self.plan = packet['campaign_plan']
                self.trace.write('native_macro_binding', dict(seq=self.count, path=str(path), commit=commit))
                self.trace.write('floor_plan', dict(run_id=raw['run_id'], floor=raw['run']['floor'], guidance=self.plan))
                pending.unlink()
                return packet
            time.sleep(.2)
        raise TimeoutError('Native macro reply/global deadline')
