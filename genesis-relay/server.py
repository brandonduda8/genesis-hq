#!/usr/bin/env python3
"""Genesis ephemeral, opaque-message relay. Never stores plaintext secrets.

This pilot is NOT approved for production secrets. The server has no decryption
keys. Messages are memory-only and are lost when the Render Free server sleeps.
"""
import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
ROOM_RE = re.compile(r"^[0-9a-f]{64}$")
B64_RE = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_BODY = 8192
MAX_MESSAGES_PER_ROOM = 64
MAX_ROOMS = 64
MESSAGE_TTL_SECONDS = 3600
IP_WINDOW_SECONDS = 60
MAX_IP_POSTS_PER_MINUTE = 20
MAX_GLOBAL_POSTS_PER_MINUTE = 120


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.rooms = {}  # room_hash => deque[{id, at, nonce, ciphertext}]
        self.counters = defaultdict(int)
        self.posts = defaultdict(deque)
        self.global_posts = deque()

    def _prune(self, now):
        old = []
        for room, items in self.rooms.items():
            while items and now - items[0]["at"] > MESSAGE_TTL_SECONDS:
                items.popleft()
            if not items:
                old.append(room)
        for room in old:
            del self.rooms[room]
        for k, attempts in list(self.posts.items()):
            while attempts and now - attempts[0] >= IP_WINDOW_SECONDS:
                attempts.popleft()
            if not attempts:
                del self.posts[k]
        while self.global_posts and now - self.global_posts[0] >= IP_WINDOW_SECONDS:
            self.global_posts.popleft()

    def append(self, room, nonce, ciphertext, ip):
        now = time.time()
        with self.lock:
            self._prune(now)
            if len(self.posts[ip]) >= MAX_IP_POSTS_PER_MINUTE or len(self.global_posts) >= MAX_GLOBAL_POSTS_PER_MINUTE:
                return None, "rate_limit"
            if room not in self.rooms and len(self.rooms) >= MAX_ROOMS:
                return None, "capacity"
            self.posts[ip].append(now)
            self.global_posts.append(now)
            self.counters[room] += 1
            item = {"id": self.counters[room], "at": now, "nonce": nonce, "ciphertext": ciphertext}
            self.rooms.setdefault(room, deque(maxlen=MAX_MESSAGES_PER_ROOM)).append(item)
            return item["id"], None

    def list(self, room, after=0):
        with self.lock:
            self._prune(time.time())
            return [dict(x) for x in self.rooms.get(room, ()) if x["id"] > after][:MAX_MESSAGES_PER_ROOM]


SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store = Store()

    def log_message(self, fmt, *args):
        # Never echo request targets, headers, message bodies or client IPs.
        pass

    def respond(self, status, payload, mime="application/json; charset=utf-8"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        for k, v in SEC_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/health":
            return self.respond(200, {"status": "ok", "mode": "synthetic-pilot", "persistent": False})
        if parsed.path in ("/", "/index.html", "/app.js", "/crypto.mjs", "/style.css"):
            name = "index.html" if parsed.path in ("/", "/index.html") else parsed.path[1:]
            mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "crypto.mjs": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
            return self.respond(200, (ROOT / "static" / name).read_bytes(), mime)
        if parsed.path == "/api/v1/messages":
            args = parse_qs(parsed.query, keep_blank_values=True)
            if set(args) - {"room", "after"} or len(args.get("room", [])) != 1 or len(args.get("after", [])) > 1:
                return self.respond(400, {"error": "bad_query"})
            room = args["room"][0]
            if not ROOM_RE.fullmatch(room):
                return self.respond(400, {"error": "bad_room"})
            raw_after = args.get("after", ["0"])[0]
            if not raw_after.isdecimal() or len(raw_after) > 15:
                return self.respond(400, {"error": "bad_cursor"})
            return self.respond(200, {"messages": self.store.list(room, int(raw_after)), "ephemeral": True})
        return self.respond(404, {"error": "not_found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/v1/messages":
            return self.respond(404, {"error": "not_found"})
        # Browser CSRF protection; nonbrowser callers are subject to quotas.
        origin = self.headers.get("Origin")
        if origin:
            scheme = self.headers.get("X-Forwarded-Proto", "https")
            if scheme not in ("https", "http"):
                return self.respond(403, {"error": "bad_origin"})
            if origin != f"{scheme}://{self.headers.get('Host', '')}":
                return self.respond(403, {"error": "bad_origin"})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.respond(415, {"error": "content_type"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.respond(400, {"error": "length"})
        if n < 2 or n > MAX_BODY:
            return self.respond(413, {"error": "size"})
        try:
            data = json.loads(self.rfile.read(n))
        except (UnicodeError, json.JSONDecodeError):
            return self.respond(400, {"error": "bad_json"})
        if not isinstance(data, dict) or set(data) != {"room", "nonce", "ciphertext"}:
            return self.respond(400, {"error": "bad_fields"})
        room, nonce, ct = data["room"], data["nonce"], data["ciphertext"]
        if not all(isinstance(v, str) for v in (room, nonce, ct)):
            return self.respond(400, {"error": "bad_fields"})
        if not ROOM_RE.fullmatch(room) or not 15 <= len(nonce) <= 32 or not B64_RE.fullmatch(nonce) or not 20 <= len(ct) <= 6144 or not B64_RE.fullmatch(ct):
            return self.respond(400, {"error": "bad_envelope"})
        id_, err = self.store.append(room, nonce, ct, self.client_address[0])
        if err:
            return self.respond(429 if err == "rate_limit" else 503, {"error": err})
        return self.respond(201, {"id": id_, "stored": "volatile"})


def serve(port=None, handler_class=Handler):
    port = int(os.environ.get("PORT", "10000")) if port is None else port
    if not 0 <= port <= 65535:
        raise ValueError("bad port")
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_class)
    server.daemon_threads = True
    print("Genesis synthetic-only relay listening", flush=True)
    return server


if __name__ == "__main__":
    with serve() as server:
        server.serve_forever(poll_interval=0.3)
