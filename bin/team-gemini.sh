#!/bin/bash
# team-gemini.sh — run one bounded Gemini work order from the team inbox.
# Usage: team-gemini.sh <work-order-file>
#
# Work-order file: plain prompt text. If the first line is "OUTBOX: <path>",
# the runner saves the worker's final message there automatically (and strips
# that line from the prompt). Otherwise the prompt must name its own outbox.
#
# Gemini is the Scout: research, verification, read-only probes, quick
# summaries. NOT hard coding — thin free-tier quota and weaker reasoning.
# Keep prompts minimal; the CLI burns several API requests per turn.
# Model override: GEMINI_MODEL (default gemini-3.5-flash).
#
# One mission at a time (one-heavy-worker policy) — never run two of these
# concurrently.
set -u
WO="${1:?usage: team-gemini.sh <work-order-file>}"
GEMINI_BIN="$HOME/workspace/bin/gemini"
[ -x "$GEMINI_BIN" ] || { echo "gemini wrapper not found" >&2; exit 2; }
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

FULL_PROMPT="You are Gemini, a bounded worker on Brandon's engineering team. Your operator is Muse (Zane). Do ONLY what the work order says. Keep your answer short and factual. Never commit, push, restart services, or reach the network beyond localhost. If anything is ambiguous, report it instead of guessing.

WORK ORDER:
$PROMPT"

if [ -n "$OUTBOX" ]; then
  "$GEMINI_BIN" -m "${GEMINI_MODEL:-gemini-3.5-flash}" -p "$FULL_PROMPT" > "$OUTBOX" 2>"$OUTBOX.err" \
    && rm -f "$OUTBOX.err" || { echo "gemini run failed (see $OUTBOX.err)" >&2; exit 1; }
  cat "$OUTBOX"
else
  exec "$GEMINI_BIN" -m "${GEMINI_MODEL:-gemini-3.5-flash}" -p "$FULL_PROMPT"
fi
