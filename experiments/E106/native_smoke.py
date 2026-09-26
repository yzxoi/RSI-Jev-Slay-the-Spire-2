"""Isolated main-menu MCP smoke; never deploys into the installed application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--app', type=Path, required=True)
parser.add_argument('--staged-mod', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--client-id', type=int, default=2026092606)
parser.add_argument('--port', type=int, default=18106)
args = parser.parse_args()
assert 1 < args.client_id < 2147483647
output = args.output.resolve()
copy = output / args.app.name
assert not copy.exists(), 'Refusing to overwrite an existing game copy'
profiles = Path.home() / 'Library/Application Support/SlayTheSpire2'
test_profile = profiles / 'default' / str(args.client_id)
assert not test_profile.exists(), 'Refusing to reuse an existing profile'
with socket.socket() as port_check:
    port_check.bind(('127.0.0.1', args.port))

def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}

def profile_hashes():
    return {str(p.relative_to(profiles)): hashlib.sha256(p.read_bytes()).hexdigest()
            for prefix in ('steam', 'default')
            for p in sorted((profiles / prefix).rglob('*'))
            if p.is_file() and not p.is_relative_to(test_profile)}

output.mkdir(parents=True, exist_ok=True)
before = profile_hashes()
installed_before = hashes(args.app)
(output / 'before-profiles.private.json').write_text(json.dumps(before))
subprocess.run(['cp', '-cR', str(args.app), str(copy)], check=True)
mods = copy / 'Contents/MacOS/mods/STS2AIAgent'
mods.mkdir(parents=True)
for name in ('STS2AIAgent.dll', 'STS2AIAgent.pck', 'mod_id.json'):
    shutil.copy2(args.staged_mod / name, mods / name)
test_profile.mkdir(parents=True)
(test_profile / 'settings.save').write_text(json.dumps({
    'schema_version': 8, 'seen_ea_disclaimer': True, 'skip_intro_logo': True,
    'mod_settings': {'mods_enabled': True, 'mod_list': [
        {'id': 'STS2AIAgent', 'is_enabled': True, 'source': 'mods_directory'}]},
    'fullscreen': False, 'language': 'en', 'volume_master': 0.0,
}))
settings = output / 'agent-settings.private.json'
settings.write_text(json.dumps({'mcpEnabled': True, 'endpoints': [], 'models': [],
                               'proactiveChatEnabled': False,
                               'hasSeenFirstRunGuide': True}))
env = dict(os.environ, STS2_AGENT_SETTINGS_PATH=str(settings),
           STS2_API_PORT=str(args.port), STS2_API_ALLOW_FALLBACK='false')
command = [str(copy / 'Contents/MacOS/Slay the Spire 2'), '--headless',
           '--audio-driver', 'Dummy', '--force-steam', 'off',
           '--clientId', str(args.client_id), '--log-file', str(output / 'godot.log')]
(output / 'command.json').write_text(json.dumps(command))
base = f'http://127.0.0.1:{args.port}'

def request(path, body=None):
    req = urllib.request.Request(base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = response.read()
        return json.loads(data) if data else None

result = {'gameplay_tested': False, 'steam_coop_tested': False, 'model_requests': 0}
with (output / 'process.log').open('w') as log:
    process = subprocess.Popen(command, env=env, stdout=log, stderr=log)
    result['pid'] = process.pid
    try:
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Game exited: {process.returncode}')
            try:
                health = request('/health')
                state = request('/state')
                if (state.get('data') or state).get('screen') == 'MAIN_MENU':
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError('Main-menu MCP startup exceeded 75s')
        for name, value in [('health', health), ('state', state)]:
            (output / f'{name}.json').write_text(json.dumps(value, indent=2))
        def rpc(method, params, rpc_id=None):
            body = {'jsonrpc': '2.0', 'method': method, 'params': params}
            if rpc_id is not None:
                body['id'] = rpc_id
            response = request('/mcp', body)
            if response and response.get('error'):
                raise RuntimeError(response['error'])
            return response
        init = rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                   'clientInfo': {'name': 'e106-stable-smoke', 'version': '1'}}, 1)
        rpc('notifications/initialized', {})
        tools = rpc('tools/list', {}, 2)
        state_rpc = rpc('tools/call', {'name': 'get_game_state', 'arguments': {}}, 3)
        if state_rpc['result'].get('isError'):
            raise RuntimeError('MCP get_game_state returned isError')
        for name, value in [('mcp-initialize', init), ('mcp-tools', tools), ('mcp-state', state_rpc)]:
            (output / f'{name}.json').write_text(json.dumps(value, indent=2))
        result['status'] = 'passed'
        result['mcp_tool_count'] = len(tools['result']['tools'])
    except Exception as exc:
        result.update(status='failed', error=str(exc))
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        result['existing_profiles_unchanged'] = before == profile_hashes()
        result['installed_application_unchanged'] = installed_before == hashes(args.app)
        (output / 'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'passed' and result['existing_profiles_unchanged'] and result['installed_application_unchanged'] else 1)
