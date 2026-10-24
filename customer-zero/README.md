# Customer Zero: owner sign-in + real host status

**Stage:** reviewable local prototype, NOT yet installed on the Ace Magic mini PC; not live on the user's phone. Python 3.11+ standard library. No model calls, customer records, deployed service, cloud spend, outbound mail, payment, A2A worker dispatch, or login provider onboarding.

## Motivation
WO-088 Milestone 1 is NOT satisfied merely by source files or a local test. The original `genesis-hq` main branch has a devcontainer + worker bridge, while relevant Foundry v0.2 and Render Nexus interfaces remain in separate draft PRs. Rather than invent worker status, this gateway measures only its actual local process/host resources and optionally probes an operator-confirmed bridge.

## Operator-only local development
1. Generate a unique **high-entropy** owner secret in the trusted host's password manager or service-secret store. Set it in environment variable `GENESIS_OWNER_TOKEN` **on the host only**; minimum 32 characters. Never paste into a chat, issue or repository.
2. From `customer-zero/`, run `python3 hq.py` with Python 3.11+. A trusted owner on the same machine can visit `http://127.0.0.1:8765` to sign in.
3. Optional read-only worker bridge probe: `python3 hq.py --bridge-path /approved/exact/bin/worker-bridge.sh`; the bridge may report READY/DOWN but this is **not** verified agent liveness, not execution or a completed task.
4. No public binding: server enforces 127.0.0.1/localhost. Phone access requires a separately reviewed, owner-approved private **HTTPS** ingress such as Tailscale Serve. Set `GENESIS_ALLOWED_HOSTS` to the exact approved private domain on the host, and review session cookies, forwarding, access rules and host protection before exposure. Do not use public tunnels, insecure HTTP beyond loopback, or arbitrary reverse proxies.

## Observations vs claims
- `/health`: only reports that this gateway process is responding.
- `GET /api/session`: authentication status (does not disclose host state when signed out).
- `POST /api/session`: validates owner token, creates a process-local 30-minute HttpOnly/SameSite cookie session, with per-IP failed-login throttle.
- `GET /api/status`: requires valid session; returns actual process uptime/PID, measured disk availability, best-effort Linux host/cgroup memory. Provider, Cody and mission ledger explicitly return NOT_CONNECTED/NOT_VERIFIED until real authenticated adapters exist.
- `POST /api/logout`: requires session and CSRF token.

Any remote or production use requires independent security review, TLS at the trusted ingress, owner identity bootstrap, session and logout QA, tested backups for persistent applications, and real supervisor/host verification. This is not a hardened multi-tenant identity provider.

## Test

```sh
python3 -m unittest discover -s tests -v
```

No owner secret is included in source or tests. Tests use synthetic fixtures; they are proof of code behavior, not of user onboarding.

## Next steps to qualify Milestone 1 and 2
1. Review/merge this narrowly into the selected Foundry/Nexus app, rather than maintaining competing production login systems.
2. Zane produces a timestamped, redacted mini-PC host/OS/service inventory and approves chosen host and private HTTPS ingress. Verify real phone login and logout using the host's own secret store, and a second-device status refresh.
3. Connect one model with a reviewed secret broker; report real provider error, quota, costs and route health. No automatic paid fallback.
4. Reuse Agent X PR #5 and the canonical Genesis Mission Ledger/Success Loop, then run one isolated synthetic bug repair and separate verifier. Repeat for three genuinely useful owner jobs, each independently reproduced with artifact SHA256 and durable receipt.
5. Never mark Customer Zero complete based only on tests or a dashboard's static labels.