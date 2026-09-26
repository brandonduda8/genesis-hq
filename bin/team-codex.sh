#!/bin/bash
# team-codex.sh — run one bounded Codex (ChatGPT) work order from the team inbox.
# Usage: team-codex.sh <work-order-file>
#
# Work-order file: plain prompt text. If the first line is "OUTBOX: <path>",
# the runner saves the worker's final message there automatically (and strips
# that line from the prompt). Otherwise the prompt must name its own outbox.
#
# The worker runs in Codex's read-only sandbox by default: it can read the
# repo and run commands, but cannot write files. Set CODEX_SANDBOX=workspace-write
# if the work order explicitly requires file writes (audited runs only).
#
# One mission at a time (one-heavy-worker policy) — never run two of these
# concurrently. Requires `codex login` (Brandon's tap) before first use.
set -u
WO="${1:?usage: team-codex.sh <work-order-file>}"
GENESIS="$HOME/workspace/genesis-os"
CODEX_BIN="${CODEX_BIN:-/opt/hatch-image/bin/codex}"
command -v "$CODEX_BIN" >/dev/null 2>&1 || CODEX_BIN="$(command -v codex || true)"
[ -n "$CODEX_BIN" ] || { echo "codex CLI not found" >&2; exit 2; }
[ -f "$WO" ] || { echo "no such work order: $WO" >&2; exit 2; }

OUTBOX=""
FIRST="$(sed -n '1p' "$WO")"
case "$FIRST" in
  OUTBOX:*)
    OUTBOX="$(printf '%s' "$FIRST" | sed 's/^OUTBOX:[[:space:]]*//')"
    PROMPT="$(tail -n +2 "$WO")"
    ;;
  *)
    PROMPT="$(cat "$WO")"
    ;;
esac

ARGS=(exec --skip-git-repo-check -C "$GENESIS" -s "${CODEX_SANDBOX:-read-only}")
[ -n "$OUTBOX" ] && ARGS+=(-o "$OUTBOX")

exec "$CODEX_BIN" "${ARGS[@]}" \
  "You are Codex, a bounded worker on Brandon's engineering team. Your operator is Muse (Zane). Do ONLY what the work order says. Never commit, push, restart services, or reach the network beyond localhost. If anything is ambiguous, report it instead of guessing.

WORK ORDER:
$PROMPT"
