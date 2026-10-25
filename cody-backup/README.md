# WO-GENESIS-CODY-RENDER-STANDBY-001

## Purpose

Use the existing free Render-hosted Genesis Alliance HQ as Cody's **owner-gated control surface** and an independent, owner-controlled Linux machine as Cody's **potential continuously running worker**. Do NOT treat Render Free as a 24/7 worker or VPN server.

## What is implemented

- `render-nexus/cody_gateway.mjs`: token-authenticated heartbeat receiver and owner-only status. It does not execute work orders. Heartbeats are in process memory and disappear on Render restarts/spin-down.
- `cody-backup/cody_backup.py`: stdlib-only, unprivileged probe for GitHub HTTPS, an optional loopback model health URL, and a bounded authenticated status report to Render. Persistent local sequence state has a lock and atomic file replacement. No credentials are saved in status. No inbound port, no firewall or VPN changes.
- Negative tests for auth, replay, malformed requests, missing tokens, staleness and model observation.
- The new web status is an observation of token possession only, NOT proof of Cody inference, signed agent identity or successful execution.

## Compute requirements and chosen placement

- **Render Free (existing):** web dashboard and observation receiver ONLY. The plan has 256 MB RAM, spins down after 15 minutes idle, is ephemeral, and shares 750 free instance hours across the workspace per month. No 24/7 worker guarantee; no free persistent disk or free background worker. Avoid unsolicited keep-alive traffic.
- **Cody host (requires owner action):** independent Linux machine with Python 3.11+, stable power, outbound HTTPS to both Render and GitHub, local persistent user storage, and a fleet supervisor/systemd. A local model is optional at first. For genuinely ongoing operation, use an existing authorized always-powered device or an eligible independent free VM with usage/idle-reclamation limits. The owner's mini PC remains on its prior hold until network and rollback verified.
- **Oracle Cloud Always Free A1** (availability and eligibility not guaranteed): current docs permit up to 2 OCPUs and 12 GB RAM of Arm compute in the home region, not a guarantee of a permanently available VM; idle instances can be reclaimed. Requires owner-controlled account setup and explicit billing controls. Google Cloud e2-micro Always Free is much smaller and not suitable for serious local coding inference.

## Operator setup (no credentials in GitHub or chat)

1. Merge only after independent review of source, run `npm run test:all` and Python tests, then deploy from the existing Render service branch with manual deployment and no paid plan changes.
2. In Render's protected environment settings for **existing** `genesis-alliance-hq`, set a unique `NEXUS_CODY_NODE_TOKEN` of at least 32 random characters, distinct from `NEXUS_OWNER_TOKEN`. Generate it on a trusted owner device (`openssl rand -hex 32`). Do not paste it in chat, commit it, or print it in log output.
3. Install the SAME token in the Cody host's private environment. Prefer host secret manager or an owner-only local environment file (chmod `0600`), not a shared directory. Do not transfer it over the failing Zane proxy route.
4. On that host, from the cloned `genesis-hq` checkout, run:

   ```bash
   python3 -B -m unittest discover -s cody-backup/tests -v
   python3 -B cody-backup/cody_backup.py doctor
   python3 -B cody-backup/cody_backup.py once
   ```

   `BLOCKED_CREDENTIALS` when no node token is present and `MODEL_MISSING` with no configured local model are accurate, not task failures to bypass.
5. From an authorized owner session, inspect:

   ```bash
   curl -fsS -H "Authorization: Bearer $NEXUS_OWNER_TOKEN" \
     https://genesis-alliance-hq.onrender.com/api/cody/status
   ```

6. After Zane and the owner confirm that this is a separate network path, choose exactly ONE supervisor mode: a persistent `watch --interval 1800` process or a scheduler invoking `once` every 1800 seconds. Do not start both. This reporting cadence is NOT an always-on guarantee for Render.

## Connectivity acceptance

- Host obtains two successive GitHub HTTPS and Render heartbeat responses at different times.
- Render shows `RECENT_TOKEN_AUTHENTICATED_SELF_REPORT` only after a real heartbeat, and `STALE_SELF_REPORT` or `NO_HEARTBEAT_OBSERVED` if absent/stale.
- A separate **authenticated** Genesis A2A challenge/ACK proves Cody-to-owner coordination. Only then can scoped coding jobs be proposed, reviewed and admitted.
- An actual Cody model invocation, deterministic test, log and signed review receipt is required before the status can be considered an active engineering worker.
- Zane's provider proxy may remain broken. This design keeps Cody productive on an independent link but cannot change Zane's provider firewall or force his outbound HTTPS to succeed.

## Security and rollback

No automatic shell execution or arbitrary HTTP command API. No public ports on Cody host. No Tailscale logout/reset, Headscale migration, mini PC changes, payment permissions or new paid Render capacity. In an emergency disable receiver by removing the Render `NEXUS_CODY_NODE_TOKEN` and stopping the host supervisor. Render data is ephemeral and is not the mission ledger. Keep all approved tasks in the authoritative Genesis/GitHub mailbox and preserve the old HQ handler.

## Headscale decision

Do not host Headscale on Render Free: Headscale needs persistent keys/database and a stable 443 HTTPS endpoint, and embedded DERP additionally uses UDP 3478. If Zane's provider blocks outbound HTTPS, self-hosting another control plane cannot guarantee connectivity. Only consider isolated Headscale on a separately reachable, owner-authorized Linux VM after proving that Zane can reach it, without migrating the existing managed Tailscale node.
