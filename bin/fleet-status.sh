#!/usr/bin/env bash
# Genesis HQ fleet observer (not an orchestrator). No agents, networks, or services are invoked.
set -eu

case "${1:-}" in
  "") FORMAT=text ;;
  --json) FORMAT=json ;;
  *) printf 'usage: fleet-status.sh [--json]\n' >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { printf 'usage: fleet-status.sh [--json]\n' >&2; exit 2; }

: "${HOME:?HOME must be set}"
AGENT_X_ROOT="${GENESIS_AGENT_X_ROOT:-$HOME/workspace/Agent-x}"
CORE_ROOT="${GENESIS_CORE_ROOT:-$HOME/workspace/genesis_core}"
MAILBOX_ROOT="${GENESIS_MAILBOX_ROOT:-$HOME/genesis-openclaw-mailbox}"

COUNT=0
[ "$FORMAT" = json ] && printf '{"schema":"genesis.fleet-observation.v1","authority":"observation-only","workers":[\n'

emit() { # identifier, observation state, evidence type: fixed identifiers only
  if [ "$FORMAT" = json ]; then
    [ "$COUNT" -eq 0 ] || printf ',\n'
    printf '  {"id":"%s","state":"%s","evidence":"%s"}' "$1" "$2" "$3"
  else
    printf 'worker=%s state=%s evidence=%s\n' "$1" "$2" "$3"
  fi
  COUNT=$((COUNT + 1))
}

cli() { # an installed binary is NOT proof of login or a running provider
  if command -v "$2" >/dev/null 2>&1; then
    emit "$1" CLI_PRESENT_UNVERIFIED path_lookup
  else
    emit "$1" NOT_OBSERVED path_lookup
  fi
}

marker() { # only inspect a known marker; never read its contents
  if [ -f "$2" ] && [ ! -L "$2" ]; then
    emit "$1" SOURCE_PRESENT_UNVERIFIED file_marker
  else
    emit "$1" NOT_OBSERVED file_marker
  fi
}

cli claude claude
cli codex codex
cli gemini gemini
cli opencode opencode
cli goose goose
cli aider aider
cli hermes hermes
cli openhands openhands
cli ruflo ruflo
cli agent_zero agent-zero
cli cody cody
cli openclaw openclaw

marker agent_x "$AGENT_X_ROOT/cody-core/codycore/registry.py"
marker genesis_core "$CORE_ROOT/genesis/kernel/adapters/registry.py"
marker openclaw_mailbox "$MAILBOX_ROOT/README.md"
# The code below is an ADAPTER only; it does not establish a live StarNet link.
if [ -f "$AGENT_X_ROOT/cody-core/codycore/starnet.py" ] &&
   [ ! -L "$AGENT_X_ROOT/cody-core/codycore/starnet.py" ]; then
  emit starnet ADAPTER_CODE_ONLY file_marker
else
  emit starnet NOT_OBSERVED file_marker
fi

# Internal names have no confirmed on-host interfaces yet. Never guess commands.
emit ace UNMAPPED owner_mapping_required
emit ghost UNMAPPED owner_mapping_required
emit prime UNMAPPED owner_mapping_required

if [ "$FORMAT" = json ]; then printf '\n]}\n'; fi
