# Offline installation fallback

Use only when Chromebook cannot fetch the SHA256-pinned bootstrap. This is an **owner-controlled local** procedure, not a request to paste scripts or credentials.

1. Download the ZIP from the current ChatGPT conversation onto the Chromebook, unpack through ChromeOS Files under **Linux files** into an owner-controlled user folder. Do not extract into system paths or as root.
2. Inspect `README.md`, `docs/CODY_FACTORY_WORK_ORDER_019.md`, and `docs/UPGRADE_RESEARCH.md`.
3. From the extracted `genesis-creatrix/` folder, launch foreground with `python3 creatrix_station.py --port 8765`, then open `http://localhost:8765` from Chrome. Stop with Ctrl+C. No installer/package changes required to run the core app.
4. For the existing Linux guest audit, run `python3 scripts/creatrix_quickstart.py --audit-only --label penguin` from that folder. No privileged settings or services touched.
5. If OpenCode or OpenHands is not present, mark `NOT_INSTALLED`. S1 remains the heavy host candidate, and SSH must first pass host-key and login verification.

Offline folder setup does not change the Chromebook firmware, Linux distro, ChromeOS, NetBird, Tailscale, SSH or user packages. Do not paste API/setup keys into this app.
