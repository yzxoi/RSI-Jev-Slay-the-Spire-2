"""Isolated HTTP transport: enforce total time even when a server drips keepalives.

Credentials travel over an anonymous stdin pipe, never argv or diagnostic logs.
The worker does not execute game actions; terminating it cannot duplicate a move.
"""
import json
import subprocess
import sys
import urllib.request
from .engine import ROOT


def post_json(endpoint, body, key, timeout):
    try:
        proc = subprocess.run([sys.executable, '-m', 'rsi.http_deadline'],
            input=json.dumps({'endpoint':endpoint,'body':body,'key':key,'timeout':timeout}),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for the child. Provider billing is unknown;
        # the caller must stop further paid calls rather than assume a free timeout.
        raise TimeoutError('HTTP total response deadline exceeded') from None
    if proc.returncode:
        raise RuntimeError('Isolated HTTP worker exited without a response')
    value = json.loads(proc.stdout)
    if value.get('transport_error'):
        raise RuntimeError(value['transport_error'].replace(key, '[redacted]'))
    return value['response']


def main():
    args = json.load(sys.stdin)
    try:
        request = urllib.request.Request(args['endpoint'],
            data=json.dumps(args['body'],ensure_ascii=False).encode(),
            headers={'Authorization':'Bearer '+args['key'],'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=args['timeout']) as response:
            result = {'response':json.load(response)}
    except Exception as exc:
        result = {'transport_error':(type(exc).__name__+': '+str(exc)).replace(args['key'],'[redacted]')}
    print(json.dumps(result))


if __name__ == '__main__': main()
