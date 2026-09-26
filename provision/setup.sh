#!/usr/bin/env bash
# Genesis HQ provisioning — runs automatically on codespace creation
# (devcontainer postCreateCommand). Idempotent: safe to re-run by hand.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$HOME/bin"

echo "=== Genesis HQ provisioning ==="

# 1. Worker bridge (Claude / Codex / Gemini lanes)
mkdir -p "$BIN_DIR"
cp "$REPO_DIR/bin/"*.sh "$BIN_DIR/"
chmod +x "$BIN_DIR/"*.sh
if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
fi
echo "[hq] worker bridge installed -> $BIN_DIR"

# 1b. Dragon OS layer
mkdir -p "$HOME/dragon"
cp -r "$REPO_DIR/dragon/"* "$HOME/dragon/"
chmod +x "$HOME/dragon/boot.sh" "$HOME/dragon/dragon"
ln -sf "$HOME/dragon/dragon" "$BIN_DIR/dragon"
mkdir -p "$REPO_DIR/inbox" "$REPO_DIR/outbox"
echo "[hq] dragon OS installed -> ~/dragon (cli: dragon {status|tools|workers|boot|laws})"

# 2. Agent CLIs (user runs the one-tap logins below afterwards)
if ! command -v npm >/dev/null 2>&1; then
  echo "[hq] npm missing, skipping CLI installs"
else
  npm install -g --no-fund --no-audit \
    @anthropic-ai/claude-code \
    @openai/codex \
    @google/gemini-cli 2>&1 | tail -2 || true
  echo "[hq] CLIs installed: $(command -v claude || echo no-claude) $(command -v codex || echo no-codex) $(command -v gemini || echo no-gemini)"
fi

# 3. Tailscale — joins the tailnet ONLY if the user set the TAILSCALE_AUTHKEY
# codespace secret (one tap at github.com/settings/codespaces or repo secrets).
# Without it HQ still works; Zane just can't SSH in until it's joined.
if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
  if ! command -v tailscale >/dev/null 2>&1; then
    curl -fsSL https://tailscale.com/install.sh | sh
  fi
  sudo tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname=genesis-hq --accept-dns=false \
    && echo "[hq] tailnet joined as genesis-hq" \
    || echo "[hq] tailscale up failed (check auth key)"
else
  echo "[hq] TAILSCALE_AUTHKEY not set — skipping tailnet join (see README)"
fi

# 4. Git identity
git config --global user.name "Brandon Duda" 2>/dev/null || true
git config --global user.email "brandonduda8@gmail.com" 2>/dev/null || true

# 5. Docker sanity
if docker info >/dev/null 2>&1; then
  echo "[hq] docker OK: $(docker --version)"
else
  echo "[hq] docker NOT available in this container"
fi

cat <<'NEXT'

=== Genesis HQ is provisioned ===
Worker bridge:  ~/bin/worker-bridge.sh {probe|run <lane> <wo-file>}
Lanes:          claude | codex | gemini  (+ goose/grok when keyed)

YOUR TAPS (one-time, inside this terminal):
  1. claude          # then /login  (Claude Pro OAuth)
  2. codex login             # approve on your phone (ChatGPT account)
  3. export GEMINI_API_KEY=...   # or add as a Codespaces secret

To let Zane SSH in: add a TAILSCALE_AUTHKEY codespace secret
(generate at https://login.tailscale.com/admin/settings/keys),
then rebuild the codespace. HQ will appear as 'genesis-hq' on the tailnet.

Free-tier budget: this box is 4-core ~= 30 hrs/month, then it pauses.
No GPU. It is a strong dev box, not a supercomputer - spend hours wisely.
NEXT

# 6. Boot Dragon OS
export PATH="$BIN_DIR:$PATH"
bash "$HOME/dragon/boot.sh" || true
