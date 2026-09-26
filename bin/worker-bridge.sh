#!/bin/bash
# worker-bridge.sh — unified dispatcher for Genesis worker lanes.
# The one door every agent (and cron) uses to hire outside muscle.
#
# Usage:
#   worker-bridge.sh probe                 # one line per lane: READY / DOWN / NEEDS_LOGIN
#   worker-bridge.sh run <lane> <wo-file>  # run one work order, flock-guarded
#
# Lanes: claude (Claude Code, Brandon's Pro OAuth), codex (ChatGPT, codex CLI),
#        gemini (Gemini CLI, free-tier API key).
# Probe-only lanes (no dispatch yet): goose, gemini — dispatched via their own
# CLIs today; the bridge reports their health so the foreman can route.
#
# One-heavy-worker policy: run holds an exclusive flock; a second concurrent
# run exits 3 immediately instead of stacking.
set -u
BIN="$HOME/workspace/bin"
LOCK="$HOME/workspace/genesis-os/state/worker-bridge.lock"

lane_status() { # $1 = lane name; prints "lane=<name> status=<READY|DOWN|NEEDS_LOGIN> detail=<...>"
  case "$1" in
    claude)
      if [ -x "$HOME/workspace/.npm-global/bin/claude" ] && [ -f "$HOME/.claude/.credentials.json" ]; then
        s=READY; d=claude-code-pro-oauth
      else s=DOWN; d=missing-cli-or-oauth; fi ;;
    codex)
      CB=/opt/hatch-image/bin/codex
      [ -x "$CB" ] || CB="$(command -v codex 2>/dev/null || true)"
      if [ -n "$CB" ] && "$CB" login status >/dev/null 2>&1; then
        s=READY; d=codex-cli-logged-in
      else s=NEEDS_LOGIN; d=run-codex-login-first; fi ;;
    goose)
      if curl -sf -m 3 http://127.0.0.1:18794/v1/models >/dev/null 2>&1; then
        s=READY; d=groq-proxy-gpt-oss-120b
      else s=DOWN; d=groq-proxy-unreachable; fi ;;
    gemini)
      if curl -sf -m 3 http://127.0.0.1:18789/v1/models >/dev/null 2>&1; then
        s=READY; d=gemini-proxy-flash-lite
      else s=DOWN; d=gemini-proxy-unreachable; fi ;;
  esac
  printf 'lane=%s status=%s detail=%s\n' "$1" "$s" "$d"
}

case "${1:?usage: worker-bridge.sh probe OR worker-bridge.sh run LANE WO-FILE}" in
  probe)
    for lane in claude codex goose gemini; do lane_status "$lane"; done
    ;;
  run)
    LANE="${2:?lane required: claude, codex, or gemini}"
    WO="${3:?work-order file required}"
    [ -f "$WO" ] || { echo "no such work order: $WO" >&2; exit 2; }
    case "$LANE" in
      claude) RUNNER="$BIN/team-claude.sh" ;;
      codex)  RUNNER="$BIN/team-codex.sh" ;;
      gemini) RUNNER="$BIN/team-gemini.sh" ;;
      *) echo "unknown lane: $LANE (claude|codex|gemini)" >&2; exit 2 ;;
    esac
    [ -x "$RUNNER" ] || { echo "runner not executable: $RUNNER" >&2; exit 2; }
    # NOTE: lock on an fd, NOT `flock file cmd || busy` — the || form also fires
    # when the runner itself fails, misreporting a failed run as "busy".
    exec 9>"$LOCK"
    flock -n 9 \
      || { echo "bridge busy: another heavy worker is running (one-heavy-worker policy)" >&2; exit 3; }
    "$RUNNER" "$WO"
    ;;
  *)
    echo "usage: worker-bridge.sh {probe|run <lane> <work-order-file>}" >&2
    exit 2
    ;;
esac
