# WO-GENESIS-CODY-CREATRIX-019 — Cody's integrated software factory

**Issued:** 2026-10-26 | **Owner:** Brandon | **Cody:** factory lead, contingent on a real host/model runtime | **Zane:** host access/inventory and installations | **Astra:** source/tests/architecture | **Security/QA:** separate reviewer | **Budget:** $0 incremental.  **Status:** Source and local tests available; **not installed on Penguin or S1**.

## Objective

Build **one** Genesis creative development workstation from existing Creatrix, Mission Forge, and A2A. Do not create a second authoritative mission database or a privileged remote shell portal. Deliver a polished local app, reproducible project starters, dev-tool discovery, read-only MCP integration, approved coding worker support, testing and proof receipts.

## Architecture and constraints

- **Penguin / ELEMI Chromebook:** interactive Creatrix UI, mission queue, source editor, Git, lightweight terminal tooling, read-only MCP, one resource-guarded local task; stop before RSS pressure freezes Crostini. No auto-start claim: Chromebook sleep can suspend Linux. Leave Tailscale, NetBird, SSH and Penguin bridge unchanged.
- **Genesis S1 / Intel N95 / reported 16 GB:** actual heavy coding jobs, model serving, OpenCode, containerized OpenHands, large tests, Docker and Node/Go/Rust compilers, user-owned project workspaces. These are **proposed deployments**, not yet installed from Astra's environment.
- **Remote links:** Penguin→S1 `192.168.1.151:22` was owner-reported TCP-open. That proves only TCP. Require S1 host fingerprint from trusted console, independent comparison, existing scoped login key and proof of login before SSH, rsync or remote development. Use private NetBird/Tailscale only; do not expose port 22 to internet, copy fleet SSH keys or start unrestricted command gateways.
- **OpenCode:** official CLI supports `opencode run`, and local MCP servers in v1 configuration. v1 and v2 permission syntax differs; lock a verified release/config first. Project-level generated OpenCode config is **ASK-before-edit/bash** and denies external-directory access and cloud fetch, and points to a read-only local MCP server. Requires real executable, authorized model and quota to count as PAIRED.
- **OpenHands:** use S1, an isolated Docker runtime, repo-scoped volume, non-root if supported, measured RAM, authenticated model, no public UI, task spending cap 0, independent security audit. Do not install on 2.7 GB Penguin. Model provider and actual CLI commands must match pinned upstream.
- **Cody:** logical principal-engineer role until an actual Cody process/tool capable model is independently verified. No claim of autonomous execution from static profiles or UI.

## Phase A — Read-only hardware/software forensic audit (owner local operator / Zane)

Read `docs/UPGRADE_RESEARCH.md`, run released SHA256-verified bootstrap as normal Linux user on Penguin, review `~/Genesis-Creatrix/reports/...`. Confirm exact board/HWID from ChromeOS Diagnostics separately. Check RAM/PSI/OOM/disk, installed tools, process/daemon inventory, thermal/battery, service reachability, permissions and backups. Return sanitized output only; never copy tokens or private paths. First measure, then decide what to remove or install.

## Phase B — Cody UI + harness (Astra source / Cody host run / independent QA)

1. Run `creatrix` as a foreground **loopback-only** web app, open http://localhost:8765, select **Cody Factory**.
2. Create one `genesis-fullstack` project. Check its mission ID in the existing Mission Forge, `GENESIS_FACTORY.json`, extension manifest permission list, MCP starter and Python tests. Inspect SHA256 evidence. No unapproved code execution from the browser.
3. `codyctl doctor`, `codyctl projects`, `codyctl inspect <slug>`, and explicitly approved `codyctl test <slug> --approve-template-tests`. Tests run **only unmodified bundled scaffold code** with timeout and a memory limit. User-edited code requires a separate isolated runner and security review.
4. Start the included `factory_mcp.py` through an approved local stdio client. Verify its three read-only tools, unknown tool denial and no file/SSH/private-token access. No MCP HTTP listener.
5. Stage `codyctl opencode-config <slug>` **after review**. This writes only the project's `opencode.json` and does not start OpenCode or configure models. Verify actual upstream version and permissions before using.
6. Provide real screenshots, test logs, source hashes and distinct SENT/RECEIVED/RUNNING/REVIEWED/VERIFIED DONE evidence states.

## Phase C — Infrastructure/tooling placement (Zane host owner + Cody)

Discover before installing: OpenSSH client and `ssh-keygen`, Git/Git LFS, rsync, Syncthing, tmux or Zellij, curl, uv/pipx, Ruff, pytest, ripgrep, fd/fzf, Python, Node.js, TypeScript, Go, Rust, Docker/Podman, Ollama and model router. Prefer **light editor+CLI on Penguin**, heavy Node/Docker/Go/Rust/model workloads on S1. Choose packages from official authenticated sources, pin versions and lock dependencies. Do not silently introduce trackers, paid APIs or public endpoints. For each installation: name owner, exact packages, disk/RAM impact, repo provenance, rollback and explicit host approval.

## Phase D — Real OpenCode and OpenHands pairing (conditional on ready host, model and approved installation)

For **OpenCode**, verify actual installation (`command -v opencode; opencode --version`), model provider availability, a reviewed local project `opencode.json`, `opencode mcp list`, and one bounded *read-only* `opencode run` before permitting edits. Confirm actual model tool calls and full receipts. Its global config and keys remain untouched by the installer.

For **OpenHands**, use a reviewed, pinned official CLI or Docker sandbox on S1 with a dedicated project mount, no host Docker socket/SSH agent or root credentials exposed to the agent, no remote port, and strict memory/disk quotas. Verify one offline synthetic project in a disposable container with real model inference before promoting it to worker READY. If model/provider/install unavailable, mark BLOCKED, not DONE.

**Do not pair by passing a shared API key in prompt or giving agents all capabilities.** Each worker has scoped identity, isolated paths and owner approval on production changes.

## Phase E — Secure transmissions and real software manufacturing

Use existing GitHub mailbox as nonsecret durable queue, NetBird private mesh for owner-consented traffic, SSH with independently pinned host keys for authorized S1 workloads, rsync over that SSH for approved artifacts only, optional Syncthing for reviewed project directories. A2A receipt is not job completion. Build CI checks, static analysis, browser extension tests, source/hashes, license scanning and signed release candidates. No publishing/merges to production without review.

## Fedora migration track — separate owner decision

Chromebook ELEMI is listed as supporting RW_LEGACY and Full ROM UEFI by MrChromebox. **Do not run firmware modification remotely**. Collect exact board and device/SSD/battery data, ChromeOS USB recovery and off-device backup, peripheral live-boot results, and explicit destructive-migration approval before Fedora 44 LXQt. Run Creatrix in Crostini first to prove useful functionality. Do not claim zram magically increases physical 4 GB RAM.

## Tests / gates

- Baseline 48 old Linux audit tests + 32 old Creatrix station tests.
- New factory/MCP/API/tests are additive, regression suite must pass before distribution.
- Security failure cases: bogus hostname, symlink workspace, traversal, modified scaffold, denied execution, invalid origin/token, no arbitrary API execution, no private key flows.
- Representative real proof: one owner-generated project → manifest → test receipt → independent review; and separate actual OpenCode/OpenHands model-reply receipts when runtimes installed.
- No unapproved expenditures. Rollback: stop local `creatrix` foreground process; local files remain owned by user, system services untouched.

## Mandatory paste receipt

```text
WO-GENESIS-CODY-CREATRIX-019
PENGUIN_LIVE_AUDIT: YES_WITH_HOST_RECEIPT / NOT_PROVEN
CPU_RAM_SWAP_CGROUP_OOM:
DISK_AND_HEALTH:
CREATRIX_INSTALLED_VERSION:
CREATRIX_UI_LOOPBACK:
FACTORY_MISSION_ID:
FACTORY_SCAFFOLD_HASHES:
FACTORY_LOCAL_TESTS:
FACTORY_MCP_STDIO:
OPENCODE_INSTALLED_AND_MODEL_CONNECTED:
OPENHANDS_INSTALLED_AND_MODEL_CONNECTED:
PENGUIN_TO_S1_TCP22: OWNER_REPORTED_OPEN
S1_HOST_KEY_VERIFIED:
S1_AUTHENTICATED_SSH:
S1_NETBIRD_PEER:
CHROMEOS_FIRMWARE_CHANGED: NO
TAILSCALE_NETBIRD_CHANGED: NO
KEYS_EXPORTED: NO
COST_USD: 0
BLOCKERS:
NEXT_OWNER_APPROVAL:
```

**Priority:** A+B source QA now. Host installation, Fedora/firmware, new SSH keys, model spend, public services and production deployment require separate narrowed approvals. No broad keys, hidden autonomy, or data deletion.
