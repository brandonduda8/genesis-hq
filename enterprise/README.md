# Genesis Enterprise MCP (draft, stdio-only)

**Status:** Stage-0 prototype. Six read-only/proposal-only MCP tools; **no outreach, real payments, external provider requests, model inference, GPU jobs, host deployments, credentials or customer-data authorization.** This package is intentionally not a running Genesis service, a bank, a financial ledger or the canonical mission database.

## Local developer smoke test (after review)
From the repository root:
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s enterprise/tests -v
python3 enterprise/mcp_server.py
```
The server speaks newline-delimited JSON-RPC over stdio. Use `initialize`, `tools/list`, and `tools/call` in a trusted *local* MCP client. It creates only an in-memory draft cache per process. Do not point unknown/untrusted clients at it. Real integration requires version negotiation, environment hardening, identity, tool authorization and independently verified tests with an official MCP SDK.

## Tools
- `system.status` — truthful demo-only status.
- `contracts.qualify` — score *unverified, caller-supplied* contract opportunities.
- `contracts.draft_proposal` — prepare a scope/quote; never submit.
- `compute.plan` — report resource estimates; never claim a worker/GPU is online.
- `pay.invoice_draft` — unissued invoice in integer cents, idempotent.
- `pay.spend_request` — owner-review request, **authorized_spend_cents=0**.

No tool marks invoices paid, captures/settles money, sends outreach, executes shell, dispatches cloud tasks, calls providers or approves its own request. In-memory SQLite is NOT the accounting ledger, has no multi-tenant access model and is unsuitable for handling real money or untrusted customers.

## Next genuine engineering steps
1. Audit and review the P0 Genesis-core payment proof freeze in draft security PR.
2. Attach a trusted authentication/identity broker, scoped grants, auditable role policy and server-side owner approval. Never accept an LLM-prompt 'approve' as a financial mandate.
3. Integrate with the *existing* Genesis Mission Ledger / Success Loop through a reviewed adapter; retain independent payment double-entry journal for money, with exact minor units and bank/provider reconciliation.
4. Connect a real processor **sandbox** after eligibility, compliance and security review. Provider-hosted checkout; signed callbacks; unique receipt; tenant/amount/currency/payee binding; replay control; no raw card/account data.
5. Implement an authenticated, reversible, rate-limited contract outreach lane only after verifying sender identity, opt-out compliance and owner-approved terms.
6. Check model/host/quota truth and isolated sandbox before training or paid inference. No automatic paid fallback.

## Warnings
The current prototype was adapted from an offline local demo with 22 passing tests. **The code in this GitHub PR differs from that local reference and must be tested against the exact commit, independently reviewed and kept in draft until readiness is established.** No user devices are modified.

Read the main product spec: [Genesis Enterprise Pay Blueprint](GENESIS_ENTERPRISE_PAY_BLUEPRINT.md).
