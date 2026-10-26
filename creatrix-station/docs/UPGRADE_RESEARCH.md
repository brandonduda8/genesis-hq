# Genesis Creatrix Station — heavy technology / optimization audit

Date: Oct 26, 2026. **Research and recommendation, not device-side deployment.**

## Hardware fact boundaries

- Earlier owner/operations record indicates Chromebook ELEMI board family, Intel Core i3-1115G4, ~4 GB host RAM with ~2.7 GB memory visible in the Linux guest, ChromeOS + Debian 13 Crostini. These are prior **reports**, not current independent on-device audit.
- MrChromebox supported device list maps ELEMI to **HP Pro c640 G2 Chromebook and HP Chromebook 14b-nb0**, with RW_LEGACY and Full ROM UEFI firmware support and CR50 write protection. See https://docs.mrchromebox.tech/docs/supported-devices . Firmware support alone **does not** guarantee peripheral/OS compatibility.
- HP's Pro c640 G2 technical documentation says its DDR4 memory is soldered/non-upgradeable. ELEMI covers multiple chassis/SKUs, so verify exact model and physical memory configuration before concluding every part or storage upgrade is possible: https://support.hp.com/us-en/product/setup-user-guides/hp-pro-c640-g2-chromebook/2100397047 . Do not buy SO-DIMM sticks expecting a RAM slot.
- Fedora 44 LXQt is a stable lightweight official Fedora variant as of this report: https://fedoraproject.org/spins/lxqt/download/ . Fedora 45 beta is not the stable target today: https://www.fedoraproject.org/spins/lxqt/download/beta/ .
- **Crostini does not equal Chromebook host**: reported Linux VM MemTotal, storage and kernel are not direct physical RAM, board flash or ChromeOS filesystem measurements. Google: https://support.google.com/chromebook/answer/9145439 and https://support.google.com/chromebook/answer/9592813 .

## Highest impact upgrades (ordered)

### A. Zero-risk immediate ChromeOS memory controls

1. Chrome `chrome://settings/performance` -> Memory Saver -> Maximum, where available. Exempt only critical live work pages. This reclaims inactive tabs; do not confuse tab suspension with new physical RAM. Source: https://support.google.com/chrome/answer/12929150 .
2. Shift+Esc Chrome Task Manager: identify heavy tabs/extensions/apps before closing. Disable unused extensions. Review Settings -> Storage management; never delete user files without backup. Source: https://support.google.com/chromebook/answer/6309225 .
3. Google ChromeOS Diagnostics app (Launcher -> Diagnostics, or Settings -> About ChromeOS -> Diagnostics) for **physical** RAM / CPU / battery tests not accessible through Linux guest. Source: https://support.google.com/chromebook/answer/10566784 .
4. ChromeOS Settings -> Developers -> Linux development environment -> Back up and restore. Save outside the Chromebook for disaster recovery before any packages or firmware. Do not run an automatic Powerwash or Linux recreation. Source: https://support.google.com/chromebook/answer/9592813 .

### B. Real user-level Linux resource governor (built now)

- Diagnose live `MemAvailable`, swap, PSI and cgroup OOM events rather than making guesses from package names.
- Admit only one heavy local worker and reserve ≥750 MiB in the **Linux runtime**, preferably more if ChromeOS/Crostini pressure observed.
- Launch explicit jobs via user `systemd-run --scope` with dynamically bounded MemoryMax, MemoryHigh and CPUQuota; fail closed when the user scope/cgroup is not available. Do **not** apply a hard memory cap to NetBird, Tailscale, SSH or the Penguin bridge, or terminate them as an "optimization".
- Avoid memory-clearing gimmicks (`drop_caches`), background "RAM booster" apps, forced swapfiles in Crostini, overcommitting with large models, or destructive "autoclean" scripts. The Linux guest cannot add host RAM or modify the ChromeOS kernel/firmware.

### C. Better kernel/OS memory management — native Fedora only

- Fedora's `zram-generator` provides **compressed swap in RAM**: it trades CPU cycles to hold compressible idle pages, possibly reducing thrash. It is *not* more physical RAM. Check actual default with `zramctl`/`swapon --show` on the installed Fedora system; defaults have changed over releases. Official: https://packages.fedoraproject.org/pkgs/zram-generator/zram-generator/ and https://fedoraproject.org/wiki/Changes/SwapOnZRAM .
- Fedora's lightweight LXQt avoids defaulting to large GNOME/KDE sessions; avoid installing both LXQt and heavy desktop suites. Use a minimal terminal/browser/editor UI and minimize autostart services.
- Keep the stock Fedora kernel, systemd and security updates; consider `tuned`/power profiles only after measuring thermals, battery and conflicting power daemons. Select **one** power manager. Avoid blindly enabling `earlyoom` alongside systemd-oomd with contradictory kill policies. Use `systemd-cgtop`, `systemd-analyze blame`, `btop` and PSI traces as evidence.
- Optional Btrfs transparent compression primarily saves **disk**, not physical RAM, and can cause extra CPU work. Compression, cache policy, THP and I/O queue tweaks must be benchmarked before adoption.

### D. Creative heavy tooling without exhausting Chromebook

- Edit and visualize locally: Chromium, VS Code/Codium or lighter Geany, terminal, Python, Git, ripgrep/fzf, tmux, btop, ncdu, FeatherPad/Obsidian alternatives (choose only what fits).
- S1: run Ollama/llama.cpp, containers, heavier Claw agents, OpenCode/Aider, builds and database services under explicit resource caps. Use authenticated SSH/NetBird; **never** expose an unauthenticated Ollama `11434` endpoint, SSH or model RPC to the public network.
- Intel i3 UHD graphics on native Fedora can benefit from Mesa acceleration and CPU+GPU-capable software where supported. Crostini virtual GPU access is version-dependent; confirm with `glxinfo`, `vainfo`, device nodes/driver checks **after** install. A hardware GPU is not conjured by CPU tuning.
- Task scheduling between Penguin and S1 is realistic; treating their RAM as one contiguous address space for arbitrary apps is not. Model sharding often loses efficiency over Wi-Fi and is only an optional carefully measured experiment.

### E. Storage and heat

- Verify exact HP SKU, physical internal storage interface, and board service manual before recommending SSD replacement. Some models have soldered eMMC; variants may contain SSD. External SSD can store repositories, assets, models and backups, **not extra RAM**.
- Keep adequate free disk space for Linux backup; the ChromeOS VM can fail to start under disk pressure. Monitor battery health, thermal throttling and charger power. Clean fans mechanically only with owner consent, power removed and appropriate guidance.

## Fedora migration gates (separate owner approval)

1. **Evidence:** exact ChromeOS model/HWID, correct ELEMI identification, `chrome://system` and Diagnostics, firmware support vs tested Fedora peripherals.
2. **Recovery:** ChromeOS USB recovery medium, verified off-device Linux .tini backup, copies of SSH public host-key identity anchors, NetBird/Tailscale *re-enrollment plan*, documented local console access, no secret export.
3. **Non-destructive testing:** live-boot Fedora 44 LXQt (where firmware allows) and verify screen, GPU, keyboard, touchpad, audio/mic/camera, Wi-Fi, USB-C charging, battery life, suspend/wake and boot behavior. Evaluate RAM/CPU/disk/thermals and GUI stability.
4. **Risk acceptance:** Full ROM UEFI may require Developer Mode, CR50 hardware write-protect steps and firmware flashing, replacing ChromeOS/verified boot and breaking ChromeOS recovery until stock firmware restoration. Backup firmware independently; brick risk exists. See https://docs.mrchromebox.tech/docs/firmware/types .
5. **No flash/partition edits until a *specific* owner approval** naming the exact device, recovery check, USB installer and rollback procedure. No remote-only firmware change. User should be physically at the device.

## Truthful performance goal

Physical Chromebook RAM remains ~4 GB until actual hardware is confirmed or replaced. Compressed swap improves some workload mix, not raw capacity; native Fedora may free some memory previously used by ChromeOS/Crostini, but exact benefit must be measured. The 16 GB reported S1 is the bigger heavy worker. Optimize for **jobs finished per hour without UI freezes** and zero incremental cost, not synthetic RAM claims.
