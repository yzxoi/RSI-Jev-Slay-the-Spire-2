"""Build an isolated upstream engine from locally owned game DLL copies."""
import json
import os
from pathlib import Path
import platform
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / "dependencies.json").read_text())
sdk = root / ".tools/dotnet"
engine = root / "vendor/sts2-cli"
sdk.parent.mkdir(exist_ok=True)
if not (sdk / "dotnet").exists():
    installer = sdk.parent / "dotnet-install.sh"
    urllib.request.urlretrieve("https://dot.net/v1/dotnet-install.sh", installer)
    subprocess.run(["bash", str(installer), "--version", lock["dotnet_sdk"],
                    "--architecture", "arm64" if platform.machine() == "arm64" else "x64",
                    "--install-dir", str(sdk), "--no-path"], check=True)
version = subprocess.check_output([str(sdk / "dotnet"), "--version"], text=True).strip()
if version != lock["dotnet_sdk"]:
    raise RuntimeError(f"SDK mismatch: {version}")
engine.parent.mkdir(exist_ok=True)
if not engine.exists():
    subprocess.run(["git", "clone", lock["headless_url"], str(engine)], check=True)
subprocess.run(["git", "checkout", "--detach", lock["headless_commit"]], cwd=engine, check=True)
for patch in sorted((root / "patches").glob("*.patch")):
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=engine, capture_output=True).returncode == 0
    if not applied:
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=engine, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=engine, check=True)
env = dict(os.environ, PATH=str(sdk) + os.pathsep + os.environ["PATH"],
           DOTNET_ROOT=str(sdk), DOTNET_CLI_TELEMETRY_OPTOUT="1")
subprocess.run(["bash", "setup.sh"], cwd=engine, env=env, check=True)
