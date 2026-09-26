"""Install only the E106-verified mod; retain private rollback/profile evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--game-app', type=Path, required=True)
p.add_argument('--package', type=Path, required=True)
p.add_argument('--record', type=Path, required=True)
a = p.parse_args()
expected = json.loads((Path(__file__).resolve().parents[1] / 'E106/results.json').read_text())
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
if subprocess.run(['pgrep', '-f', '/Contents/MacOS/Slay the Spire 2'], capture_output=True).returncode == 0:
    raise SystemExit('Game is running; refusing live installation')
data = a.game_app / 'Contents/Resources/data_sts2_macos_arm64/sts2.dll'
assert digest(data) == 'e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18'
for file in expected['adapter']['files']:
    assert digest(a.package / file['name']) == file['sha256'], file['name']
a.record.mkdir(parents=True, exist_ok=False)
support = Path.home() / 'Library/Application Support'
profiles = support / 'SlayTheSpire2/steam'
shutil.copytree(profiles, a.record / 'steam-profiles-backup')
agent = support / 'STS2AIAgent/settings.json'
if agent.exists():
    shutil.copy2(agent, a.record / 'agent-settings-backup.private.json')
target = a.game_app / 'Contents/MacOS/mods/STS2AIAgent'
if target.exists():
    raise SystemExit('Existing manual installation: inspect before replacing')
target.mkdir(parents=True)
for file in expected['adapter']['files']:
    shutil.copy2(a.package / file['name'], target / file['name'])
    assert digest(target / file['name']) == file['sha256']
record = {'status': 'installed', 'game_dll_sha256': digest(data),
          'files': expected['adapter']['files'], 'target': str(target),
          'existing_settings_modified_by_installer': False,
          'rollback': 'Close the game, then move this newly created STS2AIAgent mod directory out of the game mods directory. Never restore saved runs over newer user progress.'}
(a.record / 'installation.json').write_text(json.dumps(record, indent=2))
print(json.dumps({'status': 'installed', 'files_verified': 3, 'profiles_backed_up': True}))
