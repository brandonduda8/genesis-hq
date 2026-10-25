#!/usr/bin/env python3
"""Cody standby presence probe. Safe by default, no work-order execution.

Run on an independent, owner-controlled Linux host or eligible free VM.
The real Cody model/agent requires a separate admission and test gate.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen, build_opener, ProxyHandler

SCHEMA = 'genesis-cody-standby/1'
DEFAULT_RENDER = 'https://genesis-alliance-hq.onrender.com'
GITHUB_PROBE = 'https://api.github.com/'


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def safe_render_url(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
        raise ValueError('Render endpoint must be an HTTPS origin without credentials, path or query')
    return value.rstrip('/')


def safe_local_model_url(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != 'http' or url.hostname not in {'localhost', '127.0.0.1', '::1'} or url.username or url.password:
        raise ValueError('Model health URL must be loopback HTTP; do not expose model service')
    if not url.port or url.query or url.fragment:
        raise ValueError('Model health URL needs a loopback port and no query')
    return value


def probe_github(timeout: float = 7.0) -> bool:
    req = Request(GITHUB_PROBE, method='HEAD', headers={'User-Agent': 'genesis-cody-standby/1'})
    try:
        with urlopen(req, timeout=timeout) as result:
            return 100 <= result.status < 600
    except HTTPError as e:
        return 100 <= e.code < 600
    except (URLError, TimeoutError, OSError):
        return False


def probe_model(url: str | None, timeout: float = 3.0) -> bool | None:
    if url is None:
        return None
    safe_local_model_url(url)
    # Never allow a process-wide HTTP_PROXY to redirect a loopback probe.
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(Request(url, method='GET'), timeout=timeout) as result:
            return result.status == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def sanitize_observation(*, github: bool, model: bool | None, boot_id: str, seq: int) -> dict:
    state = ('BLOCKED_EGRESS' if not github else
             'MODEL_MISSING' if model is None else
             'MODEL_ENDPOINT_OBSERVED' if model else 'DEGRADED')
    return dict(schema=SCHEMA, node='cody-backup', boot_id=boot_id, seq=seq,
                observed_at=utcnow(), state=state,
                capabilities=['probe', 'receipt'], github_https=github, model_endpoint=model)


def post_observation(server: str, token: str | None, observation: dict, timeout: float = 10.0) -> str:
    origin = safe_render_url(server)
    if not token or len(token) < 32:
        return 'BLOCKED_CREDENTIALS'
    payload = json.dumps(observation, separators=(',', ':')).encode('utf-8')
    request = Request(origin+'/api/cody/heartbeat', data=payload, method='POST',
                      headers={'Content-Type': 'application/json',
                               'Authorization': 'Bearer '+token,
                               'User-Agent': 'genesis-cody-standby/1'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return 'RENDER_OBSERVED' if response.status in (200, 202) else 'REMOTE_NOT_ACCEPTED'
    except HTTPError as error:
        return {401: 'BLOCKED_CREDENTIALS', 503: 'RECEIVER_UNAVAILABLE',
                409: 'SEQUENCE_CONFLICT'}.get(error.code, 'REMOTE_NOT_ACCEPTED')
    except (URLError, TimeoutError, OSError):
        return 'BLOCKED_EGRESS'


def load_state(path: Path) -> dict:
    if not path.exists():
        return {'boot_id': secrets.token_hex(16), 'seq': 0}
    if path.is_symlink() or not path.is_file():
        raise ValueError('State file is not a regular file')
    try:
        data = json.loads(path.read_text('utf8'))
        if (not isinstance(data, dict) or not isinstance(data.get('boot_id'), str)
            or len(data['boot_id']) != 32 or any(c not in '0123456789abcdef' for c in data['boot_id'])
            or type(data.get('seq')) is not int or not 0 <= data['seq'] < 999999999):
            raise ValueError('Invalid state')
        return data
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError('Local state corrupt or unreadable') from error


def atomic_state(path: Path, record: dict) -> None:
    temporary = path.with_name(path.name+'.pending')
    if temporary.is_symlink():
        raise ValueError('Refusing a symlinked temporary state file')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with contextlib.suppress(FileNotFoundError):
        temporary.unlink()
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(record, output, separators=(',', ':'))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def run_once(*, state_dir: Path, server: str = DEFAULT_RENDER,
             model_url: str | None = None, token: str | None = None,
             github_probe=probe_github, model_probe=probe_model,
             publisher=post_observation) -> dict:
    safe_render_url(server)
    if model_url is not None:
        safe_local_model_url(model_url)
    if state_dir.exists() and (not state_dir.is_dir() or state_dir.is_symlink()):
        raise ValueError('Refusing unsafe state directory')
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    lock = state_dir/'watch.lock'
    if lock.is_symlink():
        raise ValueError('Refusing symlinked lock')
    with lock.open('a+') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        path = state_dir/'watch.json'
        data = load_state(path)
        seq = data['seq']+1
        pulse = sanitize_observation(github=bool(github_probe()),
                                     model=model_probe(model_url), boot_id=data['boot_id'], seq=seq)
        # Persist sequence before transmission: a lost response can be safely retried
        # with a higher sequence, not a forged duplicate.
        atomic_state(path, {'boot_id':data['boot_id'], 'seq':seq})
        delivery = publisher(server, token, pulse)
    return {'node':'cody-backup', 'observed_at':pulse['observed_at'],
            'state':pulse['state'], 'github_https':pulse['github_https'],
            'model_endpoint':pulse['model_endpoint'],
            'render_delivery':delivery, 'seq':seq,
            'execution':'NOT_ENABLED', 'model_inference':'NOT_VERIFIED'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('once','watch','doctor'))
    parser.add_argument('--state-dir', default=str(Path.home()/'.local/state/genesis-cody'))
    parser.add_argument('--server', default=DEFAULT_RENDER)
    parser.add_argument('--model-health-url', default=None)
    parser.add_argument('--interval', type=int, default=1800)
    args = parser.parse_args(argv)
    try:
        safe_render_url(args.server)
        if args.model_health_url is not None: safe_local_model_url(args.model_health_url)
        if args.interval < 900: raise ValueError('Interval must be at least 900 seconds')
        if args.mode == 'doctor':
            print(json.dumps({'state':'PREFLIGHT', 'endpoint':args.server,
              'python_ok':sys.version_info >= (3,11), 'node':'cody-backup',
              'node_token_configured':len(os.environ.get('NEXUS_CODY_NODE_TOKEN',''))>=32,
              'state_directory':str(Path(args.state_dir)), 'model_inference':'NOT_VERIFIED'},sort_keys=True))
            return 0
        stop = False
        def shutdown(_signum, _frame):
            nonlocal stop
            stop = True
        if args.mode == 'watch':
            signal.signal(signal.SIGTERM,shutdown)
            signal.signal(signal.SIGINT,shutdown)
        while not stop:
            observation = run_once(state_dir=Path(args.state_dir),server=args.server,
                model_url=args.model_health_url,token=os.environ.get('NEXUS_CODY_NODE_TOKEN'))
            print(json.dumps(observation,sort_keys=True),flush=True)
            if args.mode == 'once': break
            for _ in range(args.interval):
                if stop: break
                time.sleep(1)
        return 0
    except ValueError as error:
        print(json.dumps({'state':'BLOCKED_LOCAL_CONFIG','reason':str(error)}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
