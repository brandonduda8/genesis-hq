#!/usr/bin/env python3
"""SHA256-pinned, normal-user-only Creatrix Factory bootstrap.

Downloads exact listed source files from Genesis HQ. No sudo, packages,
service edits, SSH, VPN, firmware, keys or external code execution other than
explicit launching of the verified local application in the foreground.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

VERSION = "1.1.0"
REPO_RAW = "https://raw.githubusercontent.com/brandonduda8/genesis-hq/astra/creatrix-station-20261026/creatrix-station/"
MANIFEST = {'README.md': 'deb28cdc25dee7971d99c055210042f8d30f332c331e37232a5f66bdeecf8134', 'creatrix_station.py': '1dcf4b7a0015ed5882dc1f6540dea69c7a0186e21937fca28b783e47800f47e5', 'cody_factory.py': '91887e304ea5d516c8f8160d76565e05d7a24caa3ac31af5d74c85ebafa26d8e', 'codyctl.py': 'c64b1208e78b4c5edc9f4612de0a78dd6e8fa56c43d337f4c7de7cf200ee59cf', 'factory_mcp.py': 'ff448ab6a085b83991fb4896e590f64e395840649b871b7329aa79a397bf4212', 'web/index.html': 'de591b40524e4284d3e79f34ad3d44fdeb466ad550d0a95dc1da9e8677af017e', 'web/app.css': '113bd1153016fc5ea9cb0d0f0303ffb32b07c4a28e7907072af9273509edb1ba', 'web/app.js': '24ade4d92bc9695bdef91fbc3baa7bafc7a26b4acbdc8e90ea2dd910a00bc50b', 'scripts/creatrix_quickstart.py': '103a0731441104eeab33ee2cf84763feb890b23729d35eb8fe8d89d59b2ce37d', 'scripts/creatrix-first-pass.sh': '6ae4da98ee975395ac98b33dd33c0cf3531f41204d6a8838a48a717db1536643', 'creatrix/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'creatrix/__main__.py': '5bd648e8cff83a9e34818da7ae3ed494fa2d20979e4a8cd2faf3da83a2d825fa', 'creatrix/audit.py': '3f32c002cb97d423514ada720e5910dbe0300a5b92950dad40f5877e1539f26a', 'creatrix/compare.py': '7c7d07a07bab96d88ffd96955716aa48d927cc551afb65b2ae5ba0c58ebe1c2d', 'creatrix/dashboard.py': '853eaedc43023b15b678061fc98cb68e62cf2a3fe49fdda84d69856e3700b2bd', 'docs/UPGRADE_RESEARCH.md': '91595798258cff5791efcbca8aa7c8cc02587e327f95a7a1c50574b0dcf9e194', 'docs/WO-GENESIS-CREATRIX-018-ZANE-PASTE.md': 'f88ca1362c7d510a1a39a3340e8005b2b9c0dd0e61e10ca5fd3ae2b49e75304f', 'docs/CODY_FACTORY_WORK_ORDER_019.md': '9898bf20bb7f7ce69823cb5b5a16a5ee9ab3ce4575b50e055ef97c125203248d', 'docs/CODY_TOOLKIT_MATRIX.md': 'caa551bb5c66fc07fe599160e4c0a9bfd6c94e850f14eabaafea430cac055e92', 'docs/OFFLINE_INSTALL.md': 'ababc2fd69b88f556c0409fec41eaceff08b217a5b37425048cc15c90360452e', 'tests/test_station.py': '7cd530c65c82cc003b456df56b7fa1f70c99fbbbdc208d01e76fe1d411d066d9', 'tests/test_factory.py': '7426031367310a607f3f7fa21c7d76faeedac52dddc4e98094b3c6d47a089a4b', 'tests/test_audit.py': '9c6bac6cd69ab9444b8d6d95846ddf2c51dc213f9172b81b624bdc8d435cc04c', 'tests/test_quickstart.py': 'e49a4242252bd8a88c602bb41bb96c29fcb8c5b5b6cd50849f7acebf07a63515', 'tests/test_bootstrap.py': 'c06cf60863fe432707510d0162d3be6865281c0a280df0e05b56a221ab0b9b1c'}
MAX_FILE = 350_000


def _validate_user():
    if os.geteuid() == 0:
        raise RuntimeError('Run as ordinary Penguin user, not sudo/root')
    if sys.version_info < (3, 11):
        raise RuntimeError('Requires Python 3.11+; no packages will be installed')


def _fetch(name, checksum):
    url=REPO_RAW+name
    req=Request(url,headers={'User-Agent':'Genesis-Creatrix-Pinned-Installer/1.1','Accept':'application/octet-stream'})
    with urlopen(req,timeout=20) as response:
        data=response.read(MAX_FILE+1)
    if len(data)>MAX_FILE:
        raise RuntimeError('Download over hard limit: '+name)
    if hashlib.sha256(data).hexdigest() != checksum:
        raise RuntimeError('Source SHA256 mismatch; refusing: '+name)
    return data


def _check_release(target):
    for name,sha in MANIFEST.items():
        file=target/name
        if file.is_symlink() or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=sha:
            raise RuntimeError('Existing installation differs or damaged; refusing overwrite: '+name)


def _install_wrappers(app, binary_dir):
    if binary_dir.is_symlink(): raise RuntimeError('Symlink launcher directory refused')
    binary_dir.mkdir(parents=True,exist_ok=True)
    # First check both existing launchers before writing either one.
    for command,entry in [('creatrix','creatrix_station.py'),('codyctl','codyctl.py')]:
        path=binary_dir/command
        content='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(app/entry))+' "$@"\n'
        if path.is_symlink() or (path.exists() and path.read_text()!=content):
            raise RuntimeError('Different or symlinked launcher exists; refusing overwrite: '+str(path))
    for command,entry in [('creatrix','creatrix_station.py'),('codyctl','codyctl.py')]:
        path=binary_dir/command
        content='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(app/entry))+' "$@"\n'
        if path.is_symlink():
            raise RuntimeError('Refusing symlink launcher: '+str(path))
        if path.exists():
            if path.read_text()!=content:
                raise RuntimeError('Different launcher exists; leaving user data unchanged: '+str(path))
            continue
        with path.open('x') as f:f.write(content)
        path.chmod(0o700)


def install(home):
    _validate_user()
    root=home/'.local'/'share'/'genesis-creatrix'
    release_root=root/'releases'
    app=release_root/('creatrix-v'+VERSION)
    for p in (home/'.local',home/'.local'/'share',root,release_root,app):
        if p.is_symlink():
            raise RuntimeError('Symlink in installation path refused: '+str(p))
    release_root.mkdir(parents=True,exist_ok=True)
    if app.exists():
        _check_release(app)
        print('GENESIS_EXISTING_RELEASE_VERIFIED',flush=True)
    else:
        with tempfile.TemporaryDirectory(prefix='.creatrix-staging-',dir=release_root) as staging:
            stage=Path(staging)
            stage.chmod(0o700)
            for name,sha in MANIFEST.items():
                target=stage/name
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as f:f.write(_fetch(name,sha))
                target.chmod(0o600)
            _check_release(stage)
            # Atomic promotion on this filesystem, no overwrite of old directory.
            if app.exists():raise RuntimeError('Release appeared during installation; refusing overwrite')
            os.rename(stage,app)
        print('GENESIS_RELEASE_SHA256_VERIFIED',flush=True)
    _install_wrappers(app,home/'.local'/'bin')
    return app


def main(argv=None):
    ap=argparse.ArgumentParser(description='Genesis Creatrix Station pinned installer, no root')
    ap.add_argument('--no-launch',action='store_true',help='Verify/install but do not start UI')
    ap.add_argument('--skip-audit',action='store_true',help='Skip initial sanitized Linux guest audit')
    args=ap.parse_args(argv)
    try:
        home=Path.home().resolve()
        app=install(home)
        print('GENESIS_SOURCE='+str(app),flush=True)
        print('GENESIS_CODY_FACTORY=LOCAL_SCAFFOLD_NOT_MODEL_RUNNING',flush=True)
        if not args.skip_audit:
            # Run normal-user, report-only audit and add a bounded user-level launcher
            subprocess.run([sys.executable,str(app/'scripts'/'creatrix_quickstart.py'),'--label','penguin'],check=False,timeout=35)
        print('GENESIS_FACTORY_URL=http://localhost:8765',flush=True)
        print('GENESIS_NO_ROOT_NO_FIRMWARE_NO_NETBIRD_OR_SSH_CHANGE',flush=True)
        if args.no_launch: return 0
        print('STOP WITH Ctrl+C. No systemd service or daemon installed.',flush=True)
        os.execv(sys.executable,[sys.executable,str(app/'creatrix_station.py'),'--port','8765'])
    except Exception as e:
        print('GENESIS_INSTALL_BLOCKED: '+str(e)[:300],file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
