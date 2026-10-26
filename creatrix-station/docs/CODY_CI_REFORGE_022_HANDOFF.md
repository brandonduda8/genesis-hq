# GENESIS CREATRIX REFORGE — Cody mission 022 (Oct 26 2026)

Owner's approved scope: **read-only Chromebook/Penguin audit; reversible worktree-only development; no host/system changes**.

The source-engineering record is [WO-022](https://github.com/brandonduda8/astra-zane-bridge/issues/106). Updated Creatrix source with a strict read-only inspector and 25 tests is in the owner conversation as `Genesis_Creatrix_Reforge_Cody_022_v0.1.zip` (SHA256 `351d42da7e2742a5d9539012efaa434fd729c23749dfbce5d7cc57bfdd537c4c`). **ZIP contents are not published to this GitHub branch. Do not assume the inspector source is here.** Combined sandbox regression: 214/214 tests. No host execution proved.

## Cody immediate task
On Penguin's **existing** OpenCode 1.19.2 session, explicitly select the reported-working `opencode/glm-5.3-flash-free`. The dead `fleet-mistral/codestral-2508` default on zane-box:18798 must not be chosen. Report actual model call evidence without secrets. Preserve RAM and one-worker-only. An operator reported 836MB free and 57GB disk free on Oct 26; this is not fresh measurement.

1. Read-only audit guest RAM/cgroup current+limit/swap/PSI/OOM/process RSS/disk; distinguish *Crostini guest* from ChromeOS host. Capture sanitized before values and top processes. No credentials or unredacted configs.
2. Classify essential connectivity processes (NetBird, Tailscale, SSH, active OpenCode and bridge). **Do not stop, reconfigure, reset, export keys or disable host-key checks**.
3. Propose and only with scoped approval apply one **user-worktree-only reversible change**, then measure after values and capture exact diff/tests/commit SHA. Never claim a user-worktree edit frees host RAM without data.
4. Existing operator reported Penguin→S1 NetBird SSH success `S1_OVER_NETBIRD_OK`; verify trusted S1 SSH host fingerprint and existing authorized login (from Penguin, not Astra) before using S1 for work. S1 presently lacks Docker/Ollama/OpenHands by report; no installation approved.
5. Research ChromeOS HWID/board and evaluate stock ChromeOS+Crostini tuning, RW_LEGACY/external boot, full UEFI+Fedora LXQt. Migration **NO-GO** without owner physical console, verified backups/restoration, hardware tests, recovery image, independent S1 access and separate explicit hardware/firmware/OS-wipe tap.

**IMPORTANT:** SSH can't remain connected through device reboot/firmware flash; design for redundant service continuity on S1, a recovery channel, new trusted host-key verification, and reconnection after cutover. Never promise 100% SSH uptime on the changing host.

## Required receipt
```
CODY_REFORGE_022
MODEL_CALL:
HOST_SNAPSHOT_UTC:
MEM_AVAILABLE_BEFORE_MB:
MEM_AVAILABLE_AFTER_MB:
PSI_OOM_SWAP_AND_CGROUP:
PROCESS_CANDIDATES_AND_OWNER_APPROVAL:
PENGUIN_TO_S1_STRICT_HOSTKEY_SSH:
SSH_NETBIRD_TAILSCALE_CHANGED: NO
FIRST_WORKTREE_PATCH_SHA256:
TESTS_EXIT_CODE:
CHROMEOS_HWID_VERIFIED:
FEDORA_BOOT_PERIPHERALS_TESTED:
OS_MIGRATION_APPROVED: NO
NEW_COST_USD: 0
BLOCKER:
NEXT_OWNER_ACTION:
```

No write-protect changes, Developer Mode, firmware flashing, repartition, OS replacement, privileged changes, package installation, new services or open public ports until separate explicit review/approval.
