#!/usr/bin/env python3
"""Genesis Creatrix Station v1.0 — standard-library, loopback-only Linux cockpit.

No privilege escalation, firmware modifications, remote shell, package installs,
public service, or secret API. Read-only diagnostics + owner-local mission notes.
This file is built as a single-file release with embedded static frontend assets.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import uuid

VERSION = "1.1.0"
HTML = (Path(__file__).with_name("web") / "index.html").read_text(encoding="utf-8")
CSS = (Path(__file__).with_name("web") / "app.css").read_text(encoding="utf-8")
JS = (Path(__file__).with_name("web") / "app.js").read_text(encoding="utf-8")
HOMELAN_S1_HOST = "192.168.1.151"
HOMELAN_S1_SSH_PORT = 22
MAX_BODY = 8_192
MAX_MISSIONS = 1_000
TOOL_NAMES = ("netbird", "tailscale", "ssh", "ollama", "zeroclaw", "nanobot", "python3", "git", "docker", "go", "node", "codium")
STATE_FLOW = {"proposed": {"reviewed", "archived"}, "reviewed": {"owner_done", "archived"}, "owner_done": {"archived"}, "archived": set()}
PERSONA_SYSTEMS = {
    "muse": "You are Muse, a grounded visionary companion in Genesis Creatrix. Help people prioritize meaningful creative and technical goals. Propose actionable next steps. Never claim to have taken an action or connected to a host. Be lively, concise, warm, and practical.",
    "spark": "You are Spark, a playful product and design concept companion in Genesis Creatrix. Offer imaginative options plus one small prototype step, but distinguish ideas from completed work. No access to privileged actions. Keep responses under 130 words.",
    "forge": "You are Forge, a cautious software engineering mentor in Genesis Creatrix. Break a goal into concrete acceptance tests, safe next steps, and likely blockers. Do not claim an installation or SSH connection. Never ask for API keys or passwords. Keep responses under 130 words.",
    "sentinel": "You are Sentinel, a security-oriented companion in Genesis Creatrix. Guard against leaking credentials or acting without explicit authorization. Prefer recovery, host-key verification, test evidence and least privilege. You have no command execution permissions. Keep responses under 130 words.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_small(path: str, max_chars: int = 15_000) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:max_chars]
    except (OSError, ValueError):
        return ""


def parse_mem(raw: str) -> dict[str, int]:
    result: dict[str, int] = {}
    allowed = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    for line in raw.splitlines():
        bits = line.replace(":", " ").split()
        if len(bits) >= 2 and bits[0] in allowed and bits[1].isdigit():
            result[bits[0]] = int(bits[1]) * (1024 if len(bits) > 2 and bits[2] == "kB" else 1)
    return result


def cpu_model(raw: str) -> str:
    for line in raw.splitlines():
        if line.startswith("model name") and ":" in line:
            return line.split(":", 1)[1].strip()[:88]
    return "Linux CPU (model unavailable)"


def num_or_none(raw: str) -> int | None:
    s = raw.strip()
    return int(s) if s.isdecimal() else None


def get_cgroup_limit() -> int | None:
    return num_or_none(read_small("/sys/fs/cgroup/memory.max"))


def live_metrics() -> dict:
    """Observe only current runtime, never invent ChromeOS physical RAM."""
    m = parse_mem(read_small("/proc/meminfo"))
    total, avail = m.get("MemTotal", 0), m.get("MemAvailable", 0)
    cgroup = get_cgroup_limit()
    effective_total = min(total, cgroup) if total and cgroup else total
    current_cgroup = num_or_none(read_small("/sys/fs/cgroup/memory.current"))
    effective_avail = min(avail, max(0, cgroup - current_cgroup)) if cgroup and current_cgroup is not None else avail
    reserve = max(650 * 2**20, int(effective_total * .3)) if effective_total else 0
    if not avail or not total:
        admission = "UNKNOWN"
    elif effective_avail <= reserve + 150 * 2**20:
        admission = "CRITICAL"
    elif effective_avail < reserve + 850 * 2**20:
        admission = "GUARDED"
    else:
        admission = "READY"
    budget = max(0, min(700 * 2**20, int((effective_avail - reserve) * .5))) if admission == "READY" else 0
    alerts = []
    if admission == "CRITICAL":
        alerts.append({"level": "HIGH", "title": "Memory pressure guard", "detail": "No heavyweight local worker should start until headroom is restored."})
    elif admission == "GUARDED":
        alerts.append({"level": "NOTICE", "title": "Reserve interactive memory", "detail": "Prefer delegating heavy builds and models to S1 when authenticated."})
    swap_total = m.get("SwapTotal", 0)
    swap_free = m.get("SwapFree", 0)
    if swap_total and (swap_total - swap_free) / swap_total > .8:
        alerts.append({"level": "NOTICE", "title": "Swap heavily occupied", "detail": "Compressed or disk swap is not physical RAM; inspect pressure before adding workers."})
    try:
        use = shutil.disk_usage(Path.home())
        disk = {"total_bytes": use.total, "free_bytes": use.free}
        if use.total and use.free / use.total < .10:
            alerts.append({"level": "HIGH", "title": "Local disk low", "detail": "Review large files manually; automatic deletion is disabled."})
    except OSError:
        disk = {"total_bytes": None, "free_bytes": None}
    try:
        load = round(os.getloadavg()[0], 2)
    except (OSError, AttributeError):
        load = None
    tools = {name: shutil.which(name) is not None for name in TOOL_NAMES}
    model_names = probe_ollama_tags(timeout=.65) if tools.get("ollama") else []
    return {
        "schema": "genesis-creatrix-live/1", "time_utc": utc_now(), "version": VERSION,
        "provenance": "GUEST ONLY / NOT CHROMEOS HOST", "host_verified": False,
        "memory": {"total_bytes": total or None, "available_bytes": avail or None, "effective_available_bytes": effective_avail or None, "swap_total_bytes": swap_total, "swap_free_bytes": swap_free, "cgroup_max_bytes": cgroup, "cgroup_current_bytes": current_cgroup},
        "cpu": {"name": cpu_model(read_small("/proc/cpuinfo")), "threads": os.cpu_count(), "load1": load},
        "disk": disk,
        "admission": {"state": admission, "suggested_max_rss_bytes": budget, "one_heavy_worker_max": True, "enforced_by_kernel": False},
        "tools": tools, "local_models": model_names, "alerts": alerts,
        "safety": {"sudo_used": False, "firmware_changed": False, "config_changed": False, "keys_read": False, "remote_shell": False},
    }


def probe_ollama_tags(timeout: float = .75) -> list[str]:
    """Only talks to local loopback, never cloud providers or user-supplied URLs."""
    try:
        req = Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            payload = response.read(65_536)
        data = json.loads(payload)
        if isinstance(data, dict) and isinstance(data.get("models"), list):
            return [m["name"][:120] for m in data["models"][:8] if isinstance(m, dict) and isinstance(m.get("name"), str)]
    except (OSError, ValueError, HTTPError, URLError, TimeoutError):
        pass
    return []


def read_only_probe(action: str, data_dir: Path) -> dict:
    """Fixed diagnostic names only. Never evaluates a remote command."""
    if action == "s1_tcp":
        try:
            with socket.create_connection((HOMELAN_S1_HOST, HOMELAN_S1_SSH_PORT), timeout=3):
                result = "TCP22_OPEN"
                is_open = True
        except OSError as exc:
            result = "NOT_REACHABLE_FROM_THIS_RUNTIME"
            is_open = False
            reason = type(exc).__name__
        return {"action": action, "result": result, "port_open": is_open,
                "scope": "TCP 22 to owner-supplied S1 LAN address; NO SSH authentication", "time_utc": utc_now(),
                **({"error_type": reason} if not is_open else {})}
    if action == "agents":
        names = ("zeroclaw", "nanobot", "ollama", "openclaw", "picoclaw", "python3", "git", "go", "rustc", "node", "ssh", "netbird", "tailscale")
        return {"action": action, "result": "EXECUTABLE_PRESENCE_ONLY", "observed": {n: shutil.which(n) is not None for n in names},
                "meaning": "Presence is not proof an agent/model is running or authorized", "time_utc": utc_now()}
    if action == "ollama":
        names = probe_ollama_tags(timeout=1.5)
        return {"action": action, "result": "LOCAL_MODELS_FOUND" if names else "NO_LOCAL_MODELS_VERIFIED",
                "models": names, "meaning": "Local Ollama only; no cloud query or model installation", "time_utc": utc_now()}
    if action == "audit":
        status = live_metrics()
        status["audit"] = {"scope": "this Linux runtime only", "chromeos_host": "NOT_INSPECTED", "identity_verified": False}
        report_dir = data_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(report_dir, 0o700)
        name = "CREATRIX_AUDIT_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        path = report_dir / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(status, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return {"action": action, "result": "SANITIZED_REPORT_SAVED", "report_path": str(path), "summary": {
            "memory": status["memory"], "admission": status["admission"], "disk": status["disk"],
            "cpu": status["cpu"], "tools": status["tools"], "alerts": status["alerts"]}, "time_utc": utc_now()}
    raise ValueError("Unknown diagnostic action")


def offline_guide(persona: str, prompt: str) -> str:
    lower = prompt.lower()
    if any(word in lower for word in ("password", "secret", "api key", "setup key", "private key", "token")):
        return "Keep secrets in a vetted owner-controlled vault. Do not paste them into companion chat. We can work with redacted status, credential scope, and explicit approval steps instead."
    if "fedora" in lower or "chromebook" in lower:
        return "Creatrix evolution plan: (1) capture a real Linux audit, (2) verify ELEMI HWID and recovery media, (3) test live-USB Wi-Fi/audio/suspend, (4) only then decide whether a separately approved native Fedora LXQt switch is worth its risks. Nothing has been flashed or wiped."
    if "ram" in lower or "fast" in lower or "freeze" in lower:
        return "Treat memory as a budget, not a spell. Check available RAM, swap pressure and OOM counts. Run only one bounded local worker; put heavyweight Docker, builds and models on S1 after authentication. No software can manufacture new RAM chips."
    if "s1" in lower or "ssh" in lower or "netbird" in lower:
        return "First prove the actual route: Penguin TCP22 reachability → independently verify S1 host fingerprint → authenticate SSH with a permitted device key → check NetBird peer status. A reachable port is not SSH access. Do not transfer private keys."
    responses = {
        "muse": "Visionary move: describe the exact real-world result, then choose one small reversible step. A good mission has an owner, a success test, and an evidence receipt. Let's create that in Mission Forge.",
        "spark": "Creative spark: design one spectacular first-screen moment, then prove a tiny interaction works. For Creatrix, the glowing core looks dramatic while its real superpower is clear mission evidence. Build the smallest memorable demo.",
        "forge": "Engineering sequence: define the input, the observable output, the failure case and the rollback. Start with a local smoke test; avoid privileged changes until a verified owner approves the exact step.",
        "sentinel": "Guardian check: what changes, who authorizes it, what proves success, and how is it rolled back? A command receipt is not a connection receipt. Keep keys on authorized devices and protect existing access paths.",
    }
    return responses[persona]


def model_reply(persona: str, prompt: str, models: list[str], timeout: float = 18.0) -> tuple[str, str]:
    """Local inference only, NO tools or shell execution; strictly bounded output."""
    model = next((m for m in models if "1.5b" in m.lower()), models[0])
    payload = {"model": model, "stream": False, "messages": [
        {"role": "system", "content": PERSONA_SYSTEMS[persona]},
        {"role": "user", "content": prompt}],
        "options": {"num_predict": 170, "num_ctx": 1536, "temperature": .65}}
    request = Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read(131_072))
    message = data.get("message", {}).get("content") if isinstance(data, dict) else None
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Local model returned no textual answer")
    return message[:3_500].strip(), model


class LocalDB:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.path = self.root / "missions.sqlite3"
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS missions (id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, notes TEXT NOT NULL, state TEXT NOT NULL, created_utc TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, state TEXT NOT NULL, created_utc TEXT NOT NULL)")
        os.chmod(self.path, 0o600)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.path), timeout=4)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def list_missions(self) -> list[dict]:
        with self._lock, self._connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute("SELECT id,title,kind,notes,state,created_utc FROM missions WHERE state!='archived' ORDER BY created_utc DESC LIMIT 100")]

    def create(self, title: str, kind: str, notes: str) -> dict:
        title, notes = title.strip(), notes.strip()
        if not (1 <= len(title) <= 120) or len(notes) > 1000 or kind not in {"engineering", "creative", "research", "health"}:
            raise ValueError("Invalid mission title, notes or type")
        mission = {"id": uuid.uuid4().hex[:20], "title": title, "kind": kind, "notes": notes,
                   "state": "proposed", "created_utc": utc_now()}
        with self._lock, self._connect() as db:
            if db.execute("SELECT count(*) FROM missions").fetchone()[0] >= MAX_MISSIONS:
                raise ValueError("Mission store full; archive/export before adding more")
            db.execute("INSERT INTO missions (id,title,kind,notes,state,created_utc) VALUES (:id,:title,:kind,:notes,:state,:created_utc)", mission)
        return mission

    def update_state(self, mission_id: str, new_state: str) -> bool:
        if not isinstance(mission_id, str) or not isinstance(new_state, str):
            raise ValueError("Invalid mission state")
        with self._lock, self._connect() as db:
            row = db.execute("SELECT state FROM missions WHERE id=?", (mission_id,)).fetchone()
            if not row or new_state not in STATE_FLOW.get(row[0], set()):
                raise ValueError("Invalid mission state transition")
            db.execute("UPDATE missions SET state=? WHERE id=?", (new_state, mission_id))
        return True

    def note_observation(self, state: str):
        if state not in {"UNKNOWN", "READY", "GUARDED", "CRITICAL"}:
            return
        with self._lock, self._connect() as db:
            row = db.execute("SELECT state FROM observations ORDER BY id DESC LIMIT 1").fetchone()
            if not row or row[0] != state:
                db.execute("INSERT INTO observations (state,created_utc) VALUES (?,?)", (state, utc_now()))
                db.execute("DELETE FROM observations WHERE id NOT IN (SELECT id FROM observations ORDER BY id DESC LIMIT 150)")


def create_app(data_dir: Path, port: int = 8765, monitor: bool = True) -> ThreadingHTTPServer:
    """Tests may bind port 0; production always binds 127.0.0.1 only."""
    database = LocalDB(data_dir)
    from cody_factory import Factory
    factory = Factory(data_dir, mission_db=database)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "Creatrix/1.0"
        sys_version = ""

        def log_message(self, fmt: str, *args):
            # Minimal, never log URLs, request body or secrets.
            return

        def allowed_host(self):
            host = self.headers.get("Host", "")
            return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}", "127.0.0.1", "localhost"}

        def reply(self, code: int, content: bytes, content_type: str):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)

        def json(self, code: int, obj: dict):
            self.reply(code, json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def check_origin(self):
            origin = self.headers.get("Origin", "")
            return not origin or origin in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.allowed_host():
                return self.json(403, {"error": "Untrusted Host header"})
            path = self.path.split("?", 1)[0]
            if path in {"/", "/index.html"}:
                return self.reply(200, HTML.replace("__CREATRIX_TOKEN__", token).encode(), "text/html; charset=utf-8")
            if path == "/app.css":
                return self.reply(200, CSS.encode(), "text/css; charset=utf-8")
            if path == "/app.js":
                return self.reply(200, JS.encode(), "text/javascript; charset=utf-8")
            if path == "/health":
                return self.json(200, {"service": "genesis-creatrix", "status": "loopback-only", "mode": "local-pilot", "version": VERSION, "time_utc": utc_now()})
            if path == "/api/status":
                return self.json(200, live_metrics())
            if path == "/api/factory":
                from cody_factory import factory_snapshot
                return self.json(200, factory_snapshot(database.root))
            if path == "/api/factory/workspaces":
                from cody_factory import list_workspaces
                return self.json(200, {"projects": list_workspaces(database.root),
                                       "attestation": "SCAFFOLDS_ONLY_NO_AGENTS_EXECUTED"})
            if path == "/api/factory/integrations":
                from cody_factory import integration_plan
                return self.json(200, integration_plan())
            if path == "/api/missions":
                return self.json(200, {"missions": database.list_missions(), "meaning": "Owner-local plans, not active agent executions"})
            return self.json(404, {"error": "Not found"})

        def do_POST(self):
            if not self.allowed_host() or not self.check_origin():
                return self.json(403, {"error": "Host or origin not allowed"})
            if not secrets.compare_digest(self.headers.get("X-Creatrix-Token", ""), token):
                return self.json(403, {"error": "Missing or invalid session token"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.json(400, {"error": "Invalid request length"})
            if length < 2 or length > MAX_BODY:
                self.close_connection = True
                return self.json(413, {"error": "Request too large or missing"})
            try:
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Object required")
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                return self.json(400, {"error": "Invalid JSON object"})
            try:
                if self.path == "/api/factory/create":
                    if set(body) != {"slug", "title", "template"} or not all(isinstance(body[k], str) for k in body):
                        raise ValueError("Invalid factory creation request")
                    return self.json(201, {"workspace": factory.create_workspace(body["slug"], body["title"], body["template"])})
                if self.path == "/api/factory/inspect":
                    if set(body) != {"slug"} or not isinstance(body["slug"],str):
                        raise ValueError("Invalid workspace inspection request")
                    return self.json(200, factory.inspect_workspace(body["slug"]))
                if self.path == "/api/diagnostic":
                    action = body.get("action")
                    if not isinstance(action, str):
                        raise ValueError("Action required")
                    return self.json(200, read_only_probe(action, database.root))
                if self.path == "/api/missions":
                    if not all(isinstance(body.get(k), str) for k in ("title", "kind", "notes")):
                        raise ValueError("Invalid mission fields")
                    return self.json(201, {"mission": database.create(body["title"], body["kind"], body["notes"])})
                if self.path == "/api/mission/state":
                    database.update_state(body.get("id"), body.get("state"))
                    return self.json(200, {"state": body["state"], "meaning": "Owner-report status, NOT verified job execution"})
                if self.path == "/api/companion":
                    persona, prompt = body.get("persona"), body.get("prompt")
                    if not isinstance(persona, str) or persona not in PERSONA_SYSTEMS or not isinstance(prompt, str) or not (1 <= len(prompt.strip()) <= 800):
                        raise ValueError("Invalid persona or message")
                    health = live_metrics()
                    models = health["local_models"]
                    if models and health["memory"]["available_bytes"] and health["memory"]["available_bytes"] > 1500 * 2**20:
                        try:
                            reply, model = model_reply(persona, prompt, models)
                            return self.json(200, {"mode": "ollama", "model": model, "reply": reply, "execution": "NO_SHELL_OR_TOOLS"})
                        except (OSError, ValueError, HTTPError, URLError, TimeoutError):
                            pass
                    return self.json(200, {"mode": "offline", "model": None, "reply": offline_guide(persona, prompt), "execution": "NO_SHELL_OR_TOOLS"})
            except ValueError as exc:
                return self.json(400, {"error": str(exc)})
            return self.json(404, {"error": "Unknown API operation"})

    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = LocalServer(("127.0.0.1", port), Handler)
    server.creatrix_db = database
    server.creatrix_factory = factory
    server.creatrix_token = token
    if monitor:
        stop = threading.Event()
        def observer():
            while not stop.is_set():
                try:
                    database.note_observation(live_metrics()["admission"]["state"])
                except (OSError, sqlite3.Error):
                    pass
                stop.wait(60)
        t = threading.Thread(target=observer, name="creatrix-observer", daemon=True)
        t.start()
        server.creatrix_monitor_stop = stop
    else:
        server.creatrix_monitor_stop = None
    return server


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Genesis Creatrix local owner workbench (no sudo, offline UI)")
    p.add_argument("--port", type=int, default=8765, help="Local loopback port (default 8765)")
    p.add_argument("--data-dir", default=str(Path.home() / ".local" / "share" / "genesis-creatrix"))
    p.add_argument("--no-monitor", action="store_true", help="Disable passive pressure alerts")
    args = p.parse_args(argv)
    if os.geteuid() == 0 and os.environ.get("CREATRIX_TEST_ALLOW_ROOT") != "1":
        print("REFUSING_ROOT: Run Creatrix as an ordinary Linux user, not sudo/root.", file=sys.stderr)
        return 2
    if not 1024 <= args.port <= 65535:
        print("Port must be between 1024 and 65535.", file=sys.stderr)
        return 2
    try:
        srv = create_app(Path(args.data_dir).expanduser(), port=args.port, monitor=not args.no_monitor)
    except OSError as exc:
        print("Could not launch Creatrix locally: "+str(exc), file=sys.stderr)
        return 3
    print(f"GENESIS CREATRIX {VERSION} | LOCAL-ONLY | $0 INCREMENTAL", flush=True)
    print(f"OPEN IN CHROMEBOOK BROWSER: http://localhost:{args.port}", flush=True)
    print("No services, VPNs, firmware, or accounts were modified.", flush=True)
    try:
        srv.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:
        pass
    finally:
        if srv.creatrix_monitor_stop:
            srv.creatrix_monitor_stop.set()
        srv.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
