# Genesis Transmission v1 — Alliance HQ extension

**Runtime:** Reuses existing `genesis-alliance-hq` Render Free web service and its owner-gated GitHub mailbox. The ChatGPT sandbox does **not** host an always-on agent. Every message and ACK remains in the GitHub mailbox; no state is stored durably on Render Free's ephemeral disk.

## What is real
- `/transmission`: mobile-first operator console with in-memory owner token.
- `/api/transmission/summary`: server-side GitHub commit metadata by route, with freshness and honest connectivity states, cached for 45 seconds while the web service is awake.
- `/api/transmission/events`: owner-authenticated Server-Sent Events (SSE) while browser remains connected, with bounded streams and 45-second polling.
- `/api/transmission/delivery?route=astra-to-zane&id=msg-...`: remote source envelope and ACK with strict SHA-256 match, receiver, message ID and timestamp checks. **ACK is not cryptographic proof of agent identity or job execution.**
- `/api/transmission/plan`: explainable deterministic policy flags for risky requests, host modifications and financial effects. It **does not send or execute** anything.
- `/api/transmission/compare`: compares sanitized externally supplied vantage reports. It never pretends operator-supplied network labels prove actual network independence.
- All other existing Alliance HQ endpoints remain served by the original `server.mjs` handler. Existing `/api/message` is the only protected message publisher; it remains explicitly a `STAGED_UNACKNOWLEDGED` source, not an authenticated remote execution channel.

## Installation and test
From repo root with Node.js 20+:

```bash
npm run test:nexus
NEXUS_OWNER_TOKEN='[set in private environment]' NEXUS_GITHUB_TOKEN='[set in private environment]' npm start
```

Use Render's protected environment settings to set long unique `NEXUS_OWNER_TOKEN` (>= 32 chars) and a least-privilege repo-scoped `NEXUS_GITHUB_TOKEN`; never commit secrets or paste keys in conversation. Reuse the current variables if already configured. Without the owner token, endpoints deny access; without the GitHub token, network status reads `GITHUB_NOT_CONFIGURED` and no publication occurs.

## Runtime limits
The existing Render service is on the Free plan: cold starts, 15-minute inactivity spin-down, ephemeral local files, free instance-hour / bandwidth / build limits. **No guaranteed 24/7 uptime**, no permanent storage, and no autonomous background run while it sleeps. Account-wide usage limits and potential supplementary billing must be reviewed before enabling sustained active sessions. Do not create an additional Render service or add paid compute under the $0 spend policy.

## Outstanding gates
- The server's GitHub `NEXUS_GITHUB_TOKEN` and owner `NEXUS_OWNER_TOKEN` configuration cannot be confirmed solely from a successful deployment. Validate privately with the owner; do not reveal keys.
- Zane's provider egress remains independent of Render's GitHub egress; the web console cannot repair an upstream proxy.
- No persistent agent identity signing key is configured; hashed mailbox records are data integrity, not sender authentication.
- No actual Cody, Hermes, Zane or Claude runtime is installed or connected by this upgrade. Claude remains on hold until the owner confirms availability next week.
- A future verified identity registry, agent capability leases, signed results and cross-network challenge-response can extend the API without changing the durable mailbox.

## Operational acceptance
1. `npm run test:nexus` passes against committed head. 2. Render deployment reports successful build and live instance. 3. Operator reaches `/transmission` over TLS. 4. Authenticated `/api/transmission/summary` displays actual GitHub connectivity or explicit NOT CONFIGURED, not simulated liveness. 5. Verify a real message's remote ACK, then separately prove signed sender identity and real A2A nonce roundtrip before labelling `VERIFIED_TWO_WAY`. 6. Any controlled rollback to previous deploy preserves original gateway and mailbox.
