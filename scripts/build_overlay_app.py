#!/usr/bin/env python3
"""Build a local ignored launcher bundle so macOS identifies the overlay window."""
import argparse
from pathlib import Path
import plistlib
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--trace', required=True)
ap.add_argument('--replay', action='store_true')
a = ap.parse_args()
bundle = ROOT / 'artifacts/private/SpireOverlay.app'
contents = bundle / 'Contents'
(contents / 'MacOS').mkdir(parents=True, exist_ok=True)
(contents / 'Info.plist').write_bytes(plistlib.dumps(dict(
    CFBundleIdentifier='local.rsi.spireoverlay', CFBundleName='Spire Overlay',
    CFBundleDisplayName='Spire Overlay', CFBundleExecutable='launch',
    CFBundlePackageType='APPL', LSUIElement=True, NSHighResolutionCapable=True)))
args = [sys.executable, '-m', 'rsi.overlay', '--replay-trace' if a.replay else '--trace',
        str(Path(a.trace).absolute()), '--builtin']
if a.replay: args += ['--replay-interval', '.08']
launcher = contents / 'MacOS/launch'
launcher.write_text('#!/bin/sh\ncd ' + shlex.quote(str(ROOT)) + '\nexec ' + shlex.join(args)
                    + ' >> ' + shlex.quote(str(ROOT / 'artifacts/private/overlay-app.log')) + ' 2>&1\n')
launcher.chmod(0o755)
print(bundle)
