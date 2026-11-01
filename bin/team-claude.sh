#!/bin/bash
# team-claude.sh — run one bounded Claude Code work order from the team inbox.
# Usage: team-claude.sh <work-order-file>
# The worker may only read inside genesis-os and run shell commands; all
# writes go to the outbox result file named in the work order. One mission at
# a time (one-heavy-worker policy) — never run two of these concurrently.
set -u
WO="${1:?usage: team-claude.sh <work-order-file>}"
GENESIS="$HOME/workspace/genesis-os"
PROMPT="$(cat "$WO")"

CLAUDE_BIN="${GENESIS_CLAUDE_BIN:-$(command -v claude 2>/dev/null || true)}"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "Claude CLI not installed or not executable" >&2; exit 2; }
exec "$CLAUDE_BIN" -p \
  --add-dir "$GENESIS" \
  --allowedTools "Bash" "Read" "Write" \
  --append-system-prompt "You are Claude Code, a bounded worker on Brandon's engineering team. Your operator is Muse (Zane). Do ONLY what the work order says. Never edit files unless the work order explicitly tells you to. Never commit, push, restart services, or reach the network beyond localhost. Write your deliverable to the outbox path named in the work order. If anything is ambiguous, report it instead of guessing." \
  "$PROMPT"
