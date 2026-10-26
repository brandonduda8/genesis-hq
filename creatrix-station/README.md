# Genesis Creatrix Station + Cody Software Factory v1.1

**Status:** Build/test complete in an isolated engineering container. **Not installed on the owner's Penguin Chromebook or S1 mini PC**. Existing Tailscale, NetBird, SSH, ChromeOS, firmware, credentials and system services unchanged.

A self-hosted, loopback-only local workstation UI (no dependencies beyond Python 3.11+) with a real source scaffold factory, one existing owner-local Mission Forge database, read-only MCP over stdio, nonsecret tool inventory, and a safe Chromebook pressure-audit/guard. This is an engineering application, **not an installed autonomous model agent**.

## One paste installer — after SHA256-pinned GitHub publication

See `docs/ONE_PASTE_COMMAND.md` for the exact verified command. It downloads one small pinned bootstrap script, verifies its SHA256, and uses a file-by-file SHA256 manifest to install the v1.1 code **in an owner-owned user folder only**. It will not touch existing files if content differs, and it never runs as root. The bootstrap can start the UI in the foreground; Ctrl+C stops it. The UI will be at **http://localhost:8765**; ChromeOS Crostini may forward localhost.

If Chromebook cannot access GitHub raw over its own Internet connection, DO NOT execute insecure installer mirrors. Use the attached tested ZIP in an owner-controlled local files folder; follow the offline `docs/OFFLINE_INSTALL.md` procedure, or have an already authorized Penguin operator deploy via approved transport.

## Components

- **Creatrix command deck:** live Linux guest memory/cgroup/disk/CPU and truthful admission/alert states. No ChromeOS host modifications.
- **Companion chamber:** model-free guidance, optional real local Ollama chat only if already reachable; **no tool calls or remote shell**.
- **Mission Forge:** existing local SQLite `missions.sqlite3`, owner-reported status explicitly not independent agent verification.
- **Cody Factory:** toolchain inventory, documented OpenCode/OpenHands/MCP readiness, five self-contained project starter templates, scaffold→mission link, local source SHA256 inspection; browser endpoints never execute shell.
- **Cody CLI:** `codyctl doctor`, `projects`, `new`, `inspect`, `test --approve-template-tests`, `opencode-config`, `ssh-hostkey`. Tests only pristine bundled source templates in a bounded subprocess. This isn't an arbitrary-code runner; changed projects need a separately reviewed sandbox.
- **Factory MCP:** `python3 factory_mcp.py`, local stdio only, three read-only tools with strict schemas, no SSH/network/secrets.
- **Creatrix safe audit/guard:** `scripts/creatrix_quickstart.py`, user-only reports and optional 320–900 MiB memory-capped explicit jobs using systemd scopes. Never kills or stops existing apps.

### Commands after installation

```sh
creatrix                  # foreground, localhost:8765 (stop Ctrl+C)
codyctl doctor            # tools and present memory, source-only statuses
codyctl new my-project --title "Cody Workshop" --template genesis-fullstack
codyctl inspect my-project
codyctl test my-project --approve-template-tests  # bounded pristine generated fixture only
codyctl opencode-config my-project                # config staged; NOT paired model
codyctl mcp-command                              # see read-only MCP stdio entrypoint
codyctl ssh-hostkey --endpoint s1-lan            # untrusted public host fingerprint; no SSH login
```

**OpenCode/OpenHands are *not* installed by this package.** Real pairing requires verified installed binary/version, model/provider with known $0 cost, per-worker project permissions, and an independently witnessed run. OpenHands/Docker on S1, not the 2.7 GiB Penguin guest. SSH is permitted only with a separately verified host key and owner-authorized credential.

## Unit tests

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
```

No external network, private tokens or sudo required. Unit/fixture tests in this repository are *about the code under test, not a proof of on-device deployment.*

## Recovery and boundaries

- To stop the UI: Ctrl+C. No process runs as a daemon by default.
- To remove application launchers: inspect, then remove `~/.local/bin/creatrix` and `~/.local/bin/codyctl`. User-created projects and audit reports remain untouched. Do not delete mission database automatically.
- To switch to native Fedora, see `docs/UPGRADE_RESEARCH.md`. Do not flash firmware/disable ChromeOS verified boot without device-specific recovery tests and a separate explicit owner confirmation.
- Do not put API keys or NetBird setup keys in Creatrix UI or GitHub. NetBird's existing browser-local experimental vault is a separate prototype, not a production credential facility.

## Proof

The delivered source must have its checksum and tests recorded. Completion levels: `SOURCE_TESTED`, `HOST_INSTALLED`, `SSH_AUTHENTICATED`, `MODEL_TOOLCALL_VERIFIED`, `PRODUCTION_APPROVED`; never substitute one for another. $0 incremental cost cap.
