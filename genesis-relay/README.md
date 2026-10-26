# Genesis Relay + NetBird Key Manager — synthetic pilot

This is a **zero-cost Render Free pilot**, not a production encrypted vault or authenticated agent transport.

- `/health`: public machine-readable liveness, no secrets.
- `/`: private-room encrypted test messages (random 256-bit room secret in URL fragment) and encrypted **local-browser-only** NetBird setup-key record.
- `/api/v1/messages`: accepts **opaque** AES-GCM ciphertext only. Memory only, max 64 messages per room, 1-hour TTL, 64 rooms, rate limits. All data disappears on instance sleep/restart/redeploy.
- The service **never** receives NetBird keys, private SSH keys, Tailscale keys, PINs, recovery codes or vault passphrases. Browser code uses WebCrypto PBKDF2-SHA256 (600,000 iterations) + AES-256-GCM for its local browser record. The local encrypted record is **not backed up**, and private browser modes may remove it.
- All test-room messages are encrypted client-side using HKDF-SHA256 and AES-256-GCM, with the secret in the URI **fragment** (not sent to the origin server). Room links still expose the key to anyone who receives the link; **synthetic-only messages** until a security review with proper identities, revocation and persistence.
- A long unique master passphrase is required; never treat a short PIN as enough to encrypt API keys. Browser extensions, device compromise and clipboard sharing remain risks.
- This does **not** grant Astra/ChatGPT remote credential storage or automatically operate NetBird. An actual managed NetBird integration would require separate authenticated, limited-capability API actions, reviewed source and owner approval.

## Development

Requires Python 3.11+; no third-party packages. `python3 server.py` listens on `$PORT` or 10000. Run `python3 -m unittest discover -s tests -v`, and `node --test tests/crypto.test.mjs` when Node is available.

## Deployment

GitHub `brandonduda8/genesis-hq` on isolated branch `astra/relay-pilot-20261026`; Render service `genesis-relay-pilot` plan **free**, `autoDeploy=no`.

Build: `python3 -m compileall -q genesis-relay`
Start: `python3 genesis-relay/server.py`

No environment secrets. No pricing upgrade. Free web service sleeps; memory and messages are lost. Existing GitHub Issue #103 is the more durable **non-secret** coordination fallback. Do not use this prototype as the permanent encrypted storage of NetBird keys.

## Work order

Zane: On a known independent, authenticated browser, open Render URL, create a test room and send the nonsecret text `ZANE_RELAY_ACK` with UTC time; separately post status to GitHub Issue #103. Never enter keys or admin credentials into a chat or GitHub issue. A successful ACK proves browser communication only, not machine egress repair or a real SSH path.
