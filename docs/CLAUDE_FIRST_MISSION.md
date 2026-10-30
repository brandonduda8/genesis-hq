# Genesis / ASTRA — Claude audit-only first mission

**Status:** implementation tested offline with a mock CLI. No real Claude invocation or host deployment has been demonstrated.

This is a controlled worker **lane** in the existing `genesis-hq` bridge, not a new Genesis scheduler, database, A2A transport, or authority. The first mission is read-only and intentionally stops short of a code-editing deployment.

## Why this lane is narrow

The old `team-claude.sh` granted `Bash` and `Write` tools to a headless Claude process and relied on the prompt to limit its effects. The replacement delegates to a Python harness that:

- Requires a work order named `WO-*.txt` directly in this repository's `inbox/`, 1–4096 bytes, no symlinks or obvious credential strings.
- Requires an ASTRA checkout containing `shared/astra-workspace/MASTER_DESIGN.md`. Use the branch from ASTRA PR #117 until merged.
- Copies six **allowlisted** non-symlink documentation files into a temporary private staging directory. It does **not** hand the agent the live Genesis checkout, mailbox, credentials, or user home as working files.
- Uses Claude Code's `--restricted`, `--permission-mode dontAsk`, `--tools Read,Glob,Grep`, `--disallowedTools mcp__*`, `--max-turns 5`, and `--no-session-persistence` modes; incompatible older CLIs fail without performing the work.
- Runs Claude with a small sanitized environment. It requires `claude auth status` JSON to say `authMethod=claude.ai` and refuses API-key authentication. Using Claude Code may still consume subscription usage; the harness does not guarantee an account has enough usage remaining.
- Allows one job at a time, has a maximum timeout, and does not overwrite prior results.
- Writes an unverified text report and a JSON receipt to `outbox/`. The receipt cannot update Genesis Mission Kernel or label a job verified.

This is **not** a security boundary for a malicious operating-system user or compromised Claude executable; review the CLI version, workspace and host policies before trusting it.

## One-time setup on the chosen authorized host

1. Install or update Claude Code **using the official instructions**, and sign in as the owner (`claude auth login`) using the Claude subscription (not a usage-billed API key).
2. Clone or update `genesis-hq` and `astra-zane-bridge` into a reviewed local workspace. Set the environment variables below to their actual checkout locations.
3. Review ASTRA PR #117 and this PR; don't merge until the code is reviewed. Use the branch checkouts for the pilot if desired.
4. Run the offline unit tests below. Do not run any real job until the host and CLI have passed a read-only readiness check.

```
python3 -m unittest discover -s tests -p 'test_claude_mission.py' -v
```

## First run (after host/Claude readiness and your approval)

From the Genesis HQ working tree:

```
export GENESIS_HQ_ROOT="$PWD"
export GENESIS_ASTRA_ROOT="$HOME/workspace/astra-zane-bridge"
# Set GENESIS_ASTRA_ROOT to the actual ASTRA checkout directory.
bash bin/worker-bridge.sh run claude "$PWD/inbox/WO-ASTRA-READINESS-001.txt"
```

The result is `outbox/WO-ASTRA-READINESS-001.claude-report.md` and `...claude-receipt.json` if authentication and execution succeed. `DELIVERED_UNVERIFIED` means only that the wrapper received a nonempty successful Claude CLI output. The report must be independently inspected and reconciled with the actual Genesis ledger before being counted as verified work.

## Next phase after the pilot

Implement an explicit signed Genesis mission contract → approved execution grant → isolated disposable checkout → tests → independent Themis verification → Genesis evidence event → Phoenix status. This stage must be separately designed and reviewed; *do not* simply add Bash or Write tools to the unattended CLI wrapper.
