# Genesis Alliance HQ — remote OpenDots / AG-UI integration pilot
Status: **DRAFT PR ONLY**, not deployed or activated. Date: October 10, 2026.

## Existing remote host
Render service: `genesis-alliance-hq` (Free instance, automatic deployment disabled).
Branch: `feat/render-alliance-nexus-20261009`. Current server has bearer-protected
`/api/feed` and `/api/record` over GitHub A2A mailbox. No actual agent execution is configured.

This PR adds an **authenticated, read-only AG-UI event preview**:
`GET /api/agui/preview?route=zane-to-astra&id=msg-<32hex>`.
It reuses `/api/record` validation (GitHub contents, SHA-256) and translates
`kind=task` A2A JSON into RUN_STARTED, STATE_SNAPSHOT and RUN_FINISHED objects.
The final event only denotes **display preview** completed, NEVER the remote
agent or revenue task. The snapshot labels peer identity UNVERIFIED and any
claimed 'completed' state REVIEW_REQUIRED. Message body/tool content is not
exposed in the preview. Invalid, expired or unauthenticated records fail closed.

**This endpoint serves JSON AG-UI-shaped event objects, not a live streaming
AG-UI network endpoint or the full CopilotKit OpenDots application.**

## Remote topology (recommended)
- Phone / Chromebook: browser client only.
- Render Free Genesis Alliance HQ: low-cost authenticated status UI, read-only
  A2A/AG-UI translation and approvals visible as NOT YET GRANTED. No worker or
  authority over payment/outreach.
- Existing separately owned remote Debian server (subject to host checks):
  potential durable scheduler, task ledger, actual model workers and isolated
  computer containers, protected over an authenticated channel/Tailscale.
  This is a **proposal**; host access/runtime not verified here.
- Genesis: canonical approval and mission ledger. No second task queue.
- CopilotKit OpenDots full UI: separate **optional** investigation after license,
  Intelligence/project and model-provider costs, persistent storage and
  security hardening are proven within the $0 requirement.

## Live readiness gates (not passed by this draft)
1. Independently rerun `node --test render-nexus/test.mjs render-nexus/agui.test.mjs`
   on the exact draft SHA and review the diff before merge/deploy.
2. Ensure the existing Render service has correct `NEXUS_OWNER_TOKEN` and
   GitHub repo-scoped token configured, without disclosing secrets to chat or
   source. GET /api/health reports setup booleans only.
3. Examine Render usage caps: Free services sleep after 15m idle, have ephemeral
   storage, 750 shared hours/month, and can incur charges for usage overages
   when billing is enabled. Enforce workspace budget $0.
4. Confirm UI/API authentication, CORS/origin policy, authorizations, injection,
   rate limits, version pinning, and artifact/review semantics; hashes alone
   do not authenticate the agent.
5. Deploy only after explicit owner approval of the actual service change,
   with rollback to the previous Render deploy.
6. For true remote 24/7 workers, verify Debian host RAM/CPU/storage,
   network/firewall/Tailscale, cost, daemon governance and secrets before any
   service installation; Render Free is not a persistent always-on executor.

## Local no-dependency smoke test (for an authorized coder)
`node --test render-nexus/test.mjs render-nexus/agui.test.mjs`.
No npm modules, host secrets, paid AI services, model calls, or network
requests are needed by these hermetic tests.

## Source and requirements
- https://github.com/CopilotKit/OpenDots — MIT; template, not hosted SaaS.
- https://github.com/CopilotKit/OpenDots/blob/main/docs/SETUP.md — Node 24, Intelligence requirement.
- https://github.com/CopilotKit/OpenDots/blob/main/docs/COMPUTERS.md — isolated computers/volumes.
- https://github.com/CopilotKit/OpenDots/blob/main/SECURITY.md — remote auth and privilege boundaries.
- https://render.com/docs/free — free-tier limitations.
