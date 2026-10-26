# WO-GENESIS-CREATRIX-018 — Penguin heavyweight creative developer station

**Issued:** October 26, 2026. **Owner:** Brandon. **Host/operator:** Zane or authenticated Penguin local operator. **Architect/test:** Astra. **QA:** independent reviewer. **Budget:** $0.

## Mission
Recover usability of existing 4 GB-class ELEMI Chromebook while building a professional Genesis Creatrix creative development station integrated with the 16 GB S1. Minimize owner typing (one paste permitted); maximize verified engineering capability, not physical RAM claims.

## Gate A: Run code on the ACTUAL Penguin (P0)

- Check already-authorized terminal/executor. Astra's current ChatGPT session does **not** have Zane's `astra_zaneshell_exec`, SSH, NetBird or tailnet connectivity; a renewed grant does not expose it.
- If an authorized Penguin operator can execute, deploy Astra's audited onepaste script (full standalone source and digest on pinned public GitHub commit). Do not execute unpinned `curl | sh` or alter host network/service state.
- If not, Brandon can paste the ONE command from `docs/ONE_PASTE_COMMAND.md` into Chromebook **Linux Terminal** (not the ChromeOS crosh prompt). No sudo. Stop on hash or network failure, do not change providers.
- Save sanitized audit and local dashboard. Send only the human report or sanitized JSON, excluding arbitrary secrets. Verify output shows actual Debian/Crostini environment before treating data as Penguin.

## Gate B: Performance engineering (P0)

- Record RAM, swap, cgroup limit/current, 10/60/300 memory PSI, OOM count, top process RSS, disk free, tool/service states, systemd user scope availability, battery, physical ChromeOS Diagnostics results (owner-side UI), version and observed load.
- Identify actual source of freezes: guest OOM/cgroup, Chrome tabs, ChromeOS resource pressure, disk exhaustion, thermal, overlapping containers/agents or connectivity. **NO destructive broad service cleanup.**
- User-level Creatrix bounded launcher installs without sudo; it admits explicit jobs only with systemd cgroup controls and reserves memory. It must NOT touch the existing Zane/Penguin bridge, SSH, Tailscale, NetBird, Docker volumes, keys or boot firmware.
- Re-run audit after any separately approved change and compare MemAvailable, PSI, OOM and project-task completion under equivalent workload.

## Gate C: Heavy editor/agent toolchain (P1, only after resource evidence)

- Propose minimal Debian packages (`btop`, `ncdu`, `ripgrep`, `fzf`, `tmux`, `jq`, `zstd`, `rsync`, `python3-venv`) with apt state check and free-disk proof. Do not automatically install heavy IDEs, Docker stacks, OpenHands, multi-agent daemons, or model weights on 4GB guest.
- Use existing MissionOS/A2A and one heavy-worker slot. S1 is the 16 GB remote worker and primary host for substantial compiles, model inference and container workloads, once authorized SSH/NetBird confirmed. No public SSH/11434.
- No blanket `sudo apt full-upgrade` until backup, package/dpkg state and existing network/agent services are inspected; no ChromeOS firmware changes in this phase.

## Gate D: Fedora 44 LXQt native migration feasibility (P2 — RESEARCH ONLY)

- Confirm exact ELEMI hardware and SKU at Chromebook UI plus MrChromebox compatibility.
- Independently verify flash/write-protect/boot mode, recovery USB and off-device backup, Wi-Fi/audio/suspend/peripheral Linux compatibility. Test live distro before considering Full ROM.
- Read `docs/UPGRADE_RESEARCH.md`; record Fedora 44 official installer checksum checks and restore plan. Fedora 45 is currently beta, not the chosen stable build.
- Native Fedora replacement requires an owner-approved separately documented maintenance window; it can remove ChromeOS/verified boot and brick the device. **DO NOT RUN FIRMWARE UTILITY, DISABLE WP, OR WIPE DEVICE UNDER THIS ORDER.**

## Required receipt

```text
WO-GENESIS-CREATRIX-018
ACTUAL_HOST_AND_ACCOUNT_VERIFIED:
DEPLOYMENT_EXECUTOR_AVAILABLE:
CREATRIX_SCRIPT_SHA256_VERIFIED:
GUEST_OS_KERNEL_CPU:
LINUX_RAM_TOTAL_AVAILABLE:
CGROUP_MAX_CURRENT_OOM:
SWAP_KIND_TOTAL:
DISK_FREE:
TOP_MEMORY_PROCESSES:
CHROMEOS_DIAGNOSTICS_RESULT:
FREEZE_HYPOTHESIS_AND_EVIDENCE:
CREATRIX_USER_GUARD_INSTALLED:
GUARDED_JOB_TEST:
PENGUIN_NETBIRD_STATUS:
S1_SSH_TRUST_AND_CONNECTIVITY:
FEDORA_HWID_VERIFIED:
FEDORA_LIVE_PERIPHERALS_TESTED:
TAILSCALE_NETBIRD_SSH_UNCHANGED:
DOLLARS_SPENT: 0
STATUS: TESTED / PARTIAL / BLOCKED
NEXT_OWNER_APPROVAL:
```

**Acceptance:** No user data loss, preserved SSH and network, published exact host evidence, one bounded job and real crash/freezing improvement measured, plus a safe native Fedora migration GO/NO-GO; no claim of automatic full-OS migration.
