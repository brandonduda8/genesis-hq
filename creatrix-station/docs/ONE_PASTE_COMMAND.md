# One paste, once — Genesis Creatrix Station + Cody Factory v1.1.0

This downloads the SHA256-pinned bootstrap, verifies the exact SHA256 printed below, and runs it under the **current normal Chromebook Linux user**. No sudo, package installation, firmware change, Tailscale/NetBird/SSH modification or real model enrollment occurs. First run creates the user-local release and launches the dashboard at **http://localhost:8765**; Ctrl+C stops it.

**Copy the entire block into the Penguin Linux Terminal:**

```bash
curl --fail --location --show-error --silent --connect-timeout 10 --max-time 35 \
  https://raw.githubusercontent.com/brandonduda8/genesis-hq/astra/creatrix-station-20261026/creatrix-station/bootstrap.py \
  -o /tmp/genesis-creatrix-bootstrap-v1.py && \
printf '%s  %s\n' '0f52d43bc10a3b3b0a92cb185f875e7b2524d17d241ee2dd5472c4f84d6fce49' '/tmp/genesis-creatrix-bootstrap-v1.py' | sha256sum -c - && \
python3 /tmp/genesis-creatrix-bootstrap-v1.py
```

**Bootstrap SHA256:** `0f52d43bc10a3b3b0a92cb185f875e7b2524d17d241ee2dd5472c4f84d6fce49`.

Every downloaded source file is separately verified against a SHA256 hash embedded in the verified bootstrap. It refuses to overwrite any existing launcher with different content. The foreground app does not self-start after closing ChromeOS/Linux.

Fallback: use the ZIP attached in ChatGPT, unpack into Chromebook **Linux files** then follow `docs/OFFLINE_INSTALL.md`. Never paste key material. Never use `curl | bash` installer variants.
