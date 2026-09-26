#!/usr/bin/env bash
# boot.sh — Dragon OS boot sequence. Verifies the box is a real worker node.
# Idempotent: run anytime with `dragon boot`.
set -u
DRAGON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HQ_DIR="$(cd "$DRAGON_DIR/.." && pwd)"

say()  { printf '  [%-4s] %s\n' "$1" "$2"; }
ok()   { say "OK" "$1"; }
warn() { say "WARN" "$1"; }

echo "🐉 Dragon OS booting on $(hostname) — $(date -u '+%F %T UTC')"

# 1. Bridge on PATH and executable
if command -v worker-bridge.sh >/dev/null 2>&1; then ok "worker bridge on PATH"; else warn "worker-bridge.sh not on PATH"; fi

# 2. Lane probe
if command -v worker-bridge.sh >/dev/null 2>&1; then
  echo "  -- lane health --"
  worker-bridge.sh probe 2>/dev/null | sed 's/^/  /' || warn "probe failed"
fi

# 3. Agent CLIs
for cli in claude codex gemini; do
  if command -v "$cli" >/dev/null 2>&1; then ok "cli: $cli"; else warn "cli missing: $cli (npm install -g @$cli)"; fi
done

# 4. Docker
if docker info >/dev/null 2>&1; then ok "docker: $(docker --version | cut -d' ' -f3)"; else warn "docker unavailable"; fi

# 5. Tailnet
if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
  ok "tailnet: $(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("HostName","?"))' 2>/dev/null || echo up)"
else
  warn "not on tailnet (set TAILSCALE_AUTHKEY secret and rebuild)"
fi

# 6. Inbox / outbox
mkdir -p "$HQ_DIR/inbox" "$HQ_DIR/outbox"
ok "inbox/outbox ready"

echo "🐉 Dragon OS up. Laws: $DRAGON_DIR/LAWS.md — read them, they don't bend."
