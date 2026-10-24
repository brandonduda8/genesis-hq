"""Customer Zero: private owner login + truthful read-only host status.

Dependency-free prototype; no job execution, model calls, paid services or outbound
network traffic. For owner-controlled loopback deployment only. Not public auth.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
SESSION_TTL = 30 * 60
MAX_BODY = 2048
MAX_SESSIONS = 64
ALLOWED_LOCAL = frozenset(("localhost", "127.0.0.1"))


def _mib(n):
    return round(n / (1024 * 1024), 1) if n is not None else None


def _read_int(path):
    try:
        raw = Path(path).read_text(encoding="ascii").strip()
        return int(raw) if raw != "max" else None
    except (FileNotFoundError, PermissionError, ValueError, OSError):
        return None


def _mem_available():
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, IndexError, ValueError):
        pass
    return None


def host_snapshot(start, observed_path):
    try:
        disk = shutil.disk_usage(observed_path)
        disk_free = disk.free
        disk_total = disk.total
    except OSError:
        disk_free = disk_total = None
    return {
        "observation": "LOCAL_PROCESS_MEASURED_NOW",
        "observed_at_unix": int(time.time()),
        "process": {"pid": os.getpid(), "uptime_seconds": round(time.monotonic() - start, 1)},
        "host": {
            "logical_cpus_reported": os.cpu_count(),
            "memory_available_mib_host_estimate": _mem_available(),
            "cgroup_memory_current_mib": _mib(_read_int("/sys/fs/cgroup/memory.current")),
            "cgroup_memory_limit_mib": _mib(_read_int("/sys/fs/cgroup/memory.max")),
            "disk_free_bytes_at_project": disk_free,
            "disk_total_bytes_at_project": disk_total,
        },
        "caveats": ["Host CPU/RAM can differ from container quotas.", "Disk space is not GPU capacity."],
    }


def bridge_probe(path):
    """Read live bridge self-reports if and ONLY if the owner supplied its path.

    READY means bridge-reported readiness, not authenticated agent liveness or job
    completion. Never runs jobs or calls provider APIs intentionally.
    """
    if not path:
        return {"status": "NOT_CONFIGURED", "lanes": [], "evidence": "NO_HOST_BRIDGE_PATH"}
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        return {"status": "UNAVAILABLE", "lanes": [], "evidence": "BRIDGE_FILE_NOT_FOUND_OR_SYMLINK"}
    try:
        result = subprocess.run(["bash", str(p), "probe"], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=4, check=False,
                                env={k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "USER") if k in os.environ})
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNAVAILABLE", "lanes": [], "evidence": "BRIDGE_PROBE_FAILED"}
    if result.returncode != 0:
        return {"status": "UNAVAILABLE", "lanes": [], "evidence": "BRIDGE_PROBE_NONZERO_EXIT"}
    lanes = []
    allowed = {"READY", "DOWN", "NEEDS_LOGIN", "UNKNOWN"}
    for line in result.stdout[:4000].splitlines()[:20]:
        fields = dict(item.split("=", 1) for item in line.split() if "=" in item)
        name = fields.get("lane", "")
        state = fields.get("status", "")
        if name.isidentifier() and len(name) <= 24 and state in allowed:
            lanes.append({"name": name, "bridge_reported_state": state})
    return {"status": "BRIDGE_PROBED", "lanes": lanes,
            "evidence": "UNTRUSTED_LOCAL_CLI_REPORT_NOT_JOB_COMPLETION"}


@dataclass
class Session:
    csrf: str
    expires: float


class OwnerSessions:
    def __init__(self, owner_token):
        if not isinstance(owner_token, str) or len(owner_token) < 32 or len(owner_token) > 512:
            raise ValueError("GENESIS_OWNER_TOKEN must be a generated secret of 32-512 characters")
        self.secret = owner_token
        self.sessions: dict[str, Session] = {}
        self.failures: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def check_owner(self, owner_token, remote):
        now = time.monotonic()
        with self.lock:
            attempts = [x for x in self.failures.get(remote, []) if now - x < 60]
            if len(attempts) >= 5:
                self.failures[remote] = attempts
                return "RATE_LIMITED"
            valid = isinstance(owner_token, str) and hmac.compare_digest(owner_token, self.secret)
            if valid:
                self.failures.pop(remote, None)
                return "OK"
            self.failures[remote] = attempts + [now]
            return "DENIED"

    def create(self):
        key = secrets.token_urlsafe(32)
        session = Session(csrf=secrets.token_urlsafe(32), expires=time.monotonic() + SESSION_TTL)
        with self.lock:
            self.sessions = {k: v for k, v in self.sessions.items() if v.expires > time.monotonic()}
            if len(self.sessions) >= MAX_SESSIONS:
                self.sessions.clear()  # conservative invalidation, not arbitrary eviction
            self.sessions[key] = session
        return key, session

    def get(self, key):
        if not key:
            return None
        now = time.monotonic()
        with self.lock:
            candidate = self.sessions.get(key)
            if not candidate or candidate.expires <= now:
                self.sessions.pop(key, None)
                return None
            return candidate

    def revoke(self, key):
        with self.lock:
            self.sessions.pop(key, None)


class HQServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, owner_token, allowed_hosts=(), bridge_path=None, observed_path=None):
        if address[0] not in ("127.0.0.1", "localhost"):
            raise ValueError("Only loopback binding is allowed; use a reviewed private HTTPS ingress")
        self.auth = OwnerSessions(owner_token)
        self.allowed_hosts = ALLOWED_LOCAL | frozenset(allowed_hosts)
        self.bridge_path = bridge_path
        self.observed_path = str(observed_path or ROOT)
        self.start_time = time.monotonic()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "GenesisCustomerZero/0.1"

    def log_message(self, format, *args):
        # Do not accidentally log tokens, cookies, user input or host metadata.
        return

    def _host(self):
        header = self.headers.get("Host", "")
        if not header or len(header) > 255 or any(c in header for c in "/?#@\\"):
            return None
        try:
            p = urlsplit("http://" + header)
            if not p.hostname or p.hostname.lower() not in self.server.allowed_hosts:
                return None
            _ = p.port
        except ValueError:
            return None
        return p.hostname.lower(), header

    def _origin_ok(self, host):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        # Host and Origin must refer to the same exact authority. No CORS.
        scheme = "http" if host[0] in ALLOWED_LOCAL else "https"
        return origin == scheme + "://" + host[1]

    def _cookie_key(self):
        raw = self.headers.get("Cookie", "")
        if len(raw) > 2048:
            return ""
        try:
            c = SimpleCookie(); c.load(raw)
            return c["genesis_session"].value if "genesis_session" in c else ""
        except Exception:
            return ""

    def _session(self):
        return self.server.auth.get(self._cookie_key())

    def _reply(self, status, payload, mime="application/json; charset=utf-8", cookie=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise ValueError("JSON_REQUIRED")
        try:
            n = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            raise ValueError("INVALID_BODY")
        if n < 2 or n > MAX_BODY:
            raise ValueError("INVALID_BODY_SIZE")
        try:
            obj = json.loads(self.rfile.read(n))
        except (UnicodeError, json.JSONDecodeError):
            raise ValueError("INVALID_JSON")
        if not isinstance(obj, dict):
            raise ValueError("INVALID_OBJECT")
        return obj

    def do_GET(self):
        host = self._host()
        if not host:
            return self._reply(400, {"error": "HOST_NOT_ALLOWED"})
        path = urlsplit(self.path).path
        if path in STATIC:
            name, kind = STATIC[path]
            return self._reply(200, (ROOT / "web" / name).read_bytes(), kind)
        if path == "/health":
            return self._reply(200, {"process": "RUNNING", "detail": "NO_AGENT_ATTESTATION"})
        if path == "/api/session":
            session = self._session()
            if session is None:
                return self._reply(200, {"authenticated": False})
            return self._reply(200, {"authenticated": True, "csrf_token": session.csrf})
        if path == "/api/status":
            if self._session() is None:
                return self._reply(401, {"error": "LOGIN_REQUIRED"})
            return self._reply(200, {"status": "AUTHENTICATED_LOCAL_STATUS", "host": host_snapshot(self.server.start_time, self.server.observed_path),
                                    "worker_bridge": bridge_probe(self.server.bridge_path),
                                    "provider": {"status": "NOT_CONNECTED", "quota": None},
                                    "mission_ledger": {"status": "NOT_CONNECTED", "completed_jobs": None},
                                    "cody": {"status": "NOT_VERIFIED_RUNNING", "jobs_completed": None}})
        return self._reply(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        host = self._host()
        if not host or not self._origin_ok(host):
            return self._reply(403, {"error": "HOST_OR_ORIGIN_REJECTED"})
        path = urlsplit(self.path).path
        if path == "/api/session":
            try:
                body = self._json_body()
                if set(body) != {"owner_token"}:
                    raise ValueError("INVALID_FIELDS")
            except ValueError:
                return self._reply(400, {"error": "INVALID_LOGIN_REQUEST"})
            verdict = self.server.auth.check_owner(body["owner_token"], self.client_address[0])
            if verdict != "OK":
                return self._reply(429 if verdict == "RATE_LIMITED" else 401, {"error": "LOGIN_DENIED"})
            key, session = self.server.auth.create()
            secure = "; Secure" if host[0] not in ALLOWED_LOCAL else ""
            cookie = f"genesis_session={key}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}" + secure
            return self._reply(200, {"authenticated": True, "expires_in_seconds": SESSION_TTL, "csrf_token": session.csrf}, cookie=cookie)
        if path == "/api/logout":
            session = self._session()
            if not session:
                return self._reply(401, {"error": "LOGIN_REQUIRED"})
            if not hmac.compare_digest(self.headers.get("X-Genesis-CSRF", ""), session.csrf):
                return self._reply(403, {"error": "CSRF_REJECTED"})
            self.server.auth.revoke(self._cookie_key())
            secure = "; Secure" if host[0] not in ALLOWED_LOCAL else ""
            return self._reply(200, {"signed_out": True}, cookie="genesis_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0" + secure)
        return self._reply(404, {"error": "NOT_FOUND"})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--bridge-path", default=None, help="Optional local worker bridge script for read-only probes")
    args = parser.parse_args(argv)
    owner = os.environ.get("GENESIS_OWNER_TOKEN", "")
    hosts = tuple(s.strip().lower() for s in os.environ.get("GENESIS_ALLOWED_HOSTS", "").split(",") if s.strip())
    if any("/" in s or ":" in s or "@" in s for s in hosts):
        raise ValueError("Allowed hosts must be bare DNS hostnames")
    server = HQServer((args.bind, args.port), owner, hosts, args.bridge_path)
    print("Genesis Customer Zero running on loopback (no public deployment, no workers launched)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()