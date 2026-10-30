#!/usr/bin/env bash
# Bounded Claude worker: no Bash/Write/Edit/Web/MCP tool access in its first audit lane.
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'usage: team-claude.sh <HQ/inbox/WO-*.txt>' >&2; exit 2; fi
# Installed by the existing HQ provisioner alongside this script.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
HQ_ROOT="${GENESIS_HQ_ROOT:-$HOME/workspace/genesis-hq}"
ASTRA_ROOT="${GENESIS_ASTRA_ROOT:-$HOME/workspace/astra-zane-bridge}"
exec python3 "$SCRIPT_DIR/claude-mission.py" "$1" --hq-root "$HQ_ROOT" --astra-root "$ASTRA_ROOT" --claude-bin "${GENESIS_CLAUDE_BIN:-claude}"
