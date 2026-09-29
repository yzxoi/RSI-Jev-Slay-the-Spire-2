"""Bounded OpenRouter backend audition; never falls back to a different model."""
import json
import math
import threading
import time
from .jev import read_key
from .http_deadline import post_json

DEEPSEEK = 'deepseek/deepseek-v4.1-flash'
JEV = 'typesafe/jev-1.13'
INSTRUCTION = ('Choose the action that best preserves the chance to win the entire Slay the Spire 2 run. '
               'Consider action order, enemy threats, future turns, card/power/relic effects and resources. '
               'Use supplied current rules rather than memories of another game version. '
               'The engine will observe the result and decide again after this one action. '
               'End turn only when further plays are worse. Numeric features are limited estimates, not simulations.')


class BackendStopped(RuntimeError):
    pass


class Ledger:
    """Reserve conservative request ceilings, account all responses, stop on unknown bills."""
    def __init__(self, max_calls, max_usd):
        self.max_calls, self.max_usd = max_calls, max_usd
        self.calls = self.completed = self.failures = self.consecutive_failures = 0
        self.cost = self.reserved = self.unknown_reserved = 0.
        self.stop_reason = None
        self.lock = threading.Lock()

    def acquire(self, ceiling):
        with self.lock:
            if self.stop_reason or self.calls >= self.max_calls or self.cost + self.reserved + self.unknown_reserved + ceiling > self.max_usd:
                raise BackendStopped(self.stop_reason or 'request/spend budget exhausted')
            self.calls += 1
            self.reserved += ceiling

    def settle(self, ceiling, cost, valid):
        with self.lock:
            self.reserved -= ceiling
            self.completed += 1
            if isinstance(cost, (int, float)) and math.isfinite(cost) and cost >= 0:
                self.cost += cost
                if cost > ceiling: self.stop_reason = 'provider cost exceeded conservative reservation'
            else:
                self.unknown_reserved += ceiling
                self.stop_reason = 'unknown billing'
            if valid:
                self.consecutive_failures = 0
            else:
                self.failures += 1
                self.consecutive_failures += 1
            if self.consecutive_failures >= 3 or (self.completed >= 20 and self.failures / self.completed > .1):
                self.stop_reason = self.stop_reason or 'preregistered API reliability stop'

    def snapshot(self):
        with self.lock:
            return {k: getattr(self, k) for k in ('max_calls','max_usd','calls','completed','failures','cost','reserved','unknown_reserved','stop_reason')}


def request_body(model, payload, candidates):
    criteria = {c['id']: {k:v for k,v in c.items() if k != 'id'} for c in candidates}
    if model == JEV:
        return {'model':model, 'state':payload, 'questions':{'action':{'type':'choice','instructions':INSTRUCTION,'criteria':criteria}}}
    if model != DEEPSEEK: raise ValueError('Unregistered model')
    return {'model':model, 'messages':[
        {'role':'system','content':INSTRUCTION + ' Return only the chosen candidate ID as JSON.'},
        {'role':'user','content':json.dumps({'state':payload,'candidates':criteria}, ensure_ascii=False)}],
        'temperature':0, 'max_tokens':4096, 'reasoning':{'effort':'low','exclude':True},
        'provider':{'require_parameters':True, 'max_price':{'prompt':.5,'completion':1.5}},
        'response_format':{'type':'json_schema','json_schema':{'name':'action_choice','strict':True,
            'schema':{'type':'object','properties':{'choice':{'type':'string','enum':list(criteria)}},
                      'required':['choice'],'additionalProperties':False}}}}


def parse_choice(model, result, candidates):
    if model == JEV:
        ident = result.get('answers',{}).get('action',{}).get('choice')
    else:
        if result.get('model') != DEEPSEEK:
            raise ValueError('Unexpected returned model')
        response = result['choices'][0]
        if response.get('finish_reason') != 'stop':
            raise ValueError('Incomplete model response: ' + str(response.get('finish_reason')))
        ident = json.loads(response['message']['content'])['choice']
    chosen = next((c for c in candidates if c['id'] == ident), None)
    if chosen is None: raise ValueError('Returned choice outside legal candidates')
    return chosen


class Backend:
    def __init__(self, model, ledger):
        self.model, self.ledger, self.key = model, ledger, read_key()

    def choose(self, payload, candidates, trace):
        body = request_body(self.model, payload, candidates)
        data = json.dumps(body, ensure_ascii=False).encode()
        if len(data) > 120000: raise ValueError('Request exceeds preregistered byte ceiling')
        ceiling = (32000 * .042 / 1e6 if self.model == JEV else
                   len(data) * .5 / 1e6 + 4096 * 1.5 / 1e6)
        self.ledger.acquire(ceiling)
        trace.write('model_request', body)
        started = time.monotonic(); result = {}; valid = False
        try:
            endpoint = 'https://openrouter.ai/api/v1/' + ('systemone' if self.model == JEV else 'chat/completions')
            result = post_json(endpoint, body, self.key, 25 if self.model == JEV else 45)
            trace.write('model_response', {'response':result,'seconds':time.monotonic()-started})
            chosen = parse_choice(self.model, result, candidates)
            valid = True
            return chosen
        except Exception as exc:
            trace.write('model_failure', {'type':type(exc).__name__,
                        'message':str(exc).replace(self.key, '[redacted]'),'seconds':time.monotonic()-started})
            raise
        finally:
            self.ledger.settle(ceiling, result.get('usage',{}).get('cost'), valid)
