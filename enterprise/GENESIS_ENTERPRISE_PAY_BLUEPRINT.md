# Genesis Enterprise + Genesis Pay — governed autonomous company OS (RFC)
**2026-10-24 | DESIGN / WORKER NOT DEPLOYED | new spend ceiling: $0**
**Owner direction:** reduce owner setup burden, sell verified AI/software contracts first, services second, R&D third. Build a legitimate, secure agent-payment operating system that prevents AI from making unauthorized financial actions. NO real-money permissions follow from this document.

## Executive architecture
Owner/Phoenix UI -> trusted policy and scoped approvals -> canonical Genesis Mission Ledger -> existing Operator Continuity + Success Loop -> Zane operator host (when proven) -> Cody/Claude/QA workers and selected licensed providers -> evidence/receipts -> delivered customer result.
Genesis Pay is a **separate financial subsystem** with a proper transactional payment ledger, linked by immutable mission references. **It is not a duplicate mission ledger.** A GitHub ACK/LLM statement is never proof of delivery, customer acceptance, payment or income.

### Tool boundaries (MCP)
Use narrowly scoped MCP capability servers rather than one super-root API:
- **contracts-research:** candidate listings, eligibility, deadline and price checks; VERIFIED only if source/time current; no autonomous messages.
- **contracts-proposal:** customer-safe draft SOW, milestone plan, quote and scope validation; owner approves transmission.
- **cody-forge:** branch/worktree, isolated build, exact-head tests, SBOM, artifact digests; independent QA and PR.
- **compute-broker:** read-only CPU/RAM/GPU/host/quota probes -> task fit -> bounded leases; dispatch only to proven isolated workers with measured $0 quota.
- **model-router:** small on-device transformer for safe classification, competent remote medium/large models for coding/STEM if available and authorized, independent verifier. Router cannot invent GPU/memory.
- **starnet-adapter:** reviewed localhost sidecar from StarNet pilot PR #23 with isolated user and Genesis approval/ledger; no second financial authority.
- **genesis-pay:** draft invoice, preview payment authorization, risk and budget check, provider sandbox verification and reconciliation. Live capture/payment/refunds are **not implemented** in Phase 0.
- **outreach:** draft and unsubscribe screening. Live outbound transmission requires verified recipient/consent/compliance, sending identity, rate caps, audit and separately scoped owner permission. NO unsolicited blasting.

All servers validate schemas server-side, fail closed on unknown identity/host/permissions/cost, and never treat LLM prompts or web content as privileged authorization. No raw secrets in prompts, tools, artifacts, logs, source or GitHub. Use existing proposed vault broker only after independent review.

## Genesis Pay — user safety / agent commerce
**Product wedge:** owner-controlled invoices + quotes + legitimate provider-hosted checkout; later agent expense mandates and external customer accounts once compliance established.
**Payment control plane:** human/device authentication + signed intent mandates/one-time approvals; merchant and payee allowlist; exact minor-unit amount/currency; per-transaction/period cap; purpose and work-order binding; expiration, frequency, velocity and anomaly rules; separate merchant reputation checks; user-visible revoke/STOP; full audit and reasoned receipts. Agent CANNOT approve its own purchase.
**Money layer:** provider-hosted card/ACH/wallet rails through licensed processor/bank; tokenize payment method at provider; do not store raw PAN, CVV, bank credentials, private keys or customer wallet seeds; no new custodial wallet or money transmission without legal/provider approval.
**Financial state:** append-only double-entry ledger with integer minor units, unique provider transaction identifiers, signed webhook verification, transaction-level idempotency, replay/ordering/currency/merchant checks, refunds via reversing entries, settlement reconciliation independent of AI. Unknown external effect => RECONCILIATION_REQUIRED, never blind retry.
**Protocol research:** AP2 signed verifiable mandates for authorization, MCP tools and A2A interaction, x402 only for optional paid APIs under explicit budgets, UCP/ACP for compatible merchants as appropriate. No direct agent-wallet/crypto sends in Phase 0. Audit standards/licenses before implementing. Protect user from prompt injection and impersonation, not just theft by malicious agents.

### P0 exploit containment — discovered from current Genesis-core source
`genesis/economics/payment_gateway.py` accepts Cash App proof with `verified=True` unconditionally; PayPal capture is treated as Boolean rather than receipt-bound merchant/amount/currency/tenant verification; Base ETH proof does not verify sufficient value; Base USDC transfer proofs are not invoice-unique; invoice sums use floats/SQLite REAL; access keys are stored raw in the same invoice table. A **separate draft fail-closed PR** must first suspend unsafe auto-provisioning while verified adapters and replay-safe ledger are implemented. Do not merge just because tests pass; obtain security review and potential migration plan. Current deployment unknown. Existing `pay-test.js` synthetic event is not settlement proof.

## Autonomous business loop (90-day gates)
1. **Find:** source-verified AI automation/QA opportunities, no invented client identity.
2. **Qualify:** eligibility, scope, price, deadline, terms, cost-to-serve, data access/insurance and payment viability.
3. **Propose:** Cody generates bounded project plan and bid *draft*; QA independently checks technical feasibility; owner approves first outreach/signature.
4. **Build:** isolated repo branch and approved sandbox; tests red->green, lint, security scan, executable demo and reproducible hashes.
5. **Deliver:** owner/customer acceptance; no fake sent/delivered statuses.
6. **Invoice:** draft amount in exact cents; provider creates hosted checkout only after owner onboarding/approval.
7. **Reconcile:** signed provider receipt + settlement proof, independent ledger journal, no duplicated fulfillment.
8. **Learn:** measure win rate, gross margin, verified net profit, satisfaction, defect/rework rate, cost and energy; reallocate verified $0 spare resources.

**0-30 days:** security hold on unsafe gateway, one real reproducible demo, 20 independently verified eligible opportunities, 5 owner-review-ready proposals.
**31-60 days:** reviewed sandbox invoice/processor adapter, first owner-approved proposals and customer delivery if contracts awarded.
**61-90 days:** independent stability/failure drill, first verified settlement and repeatable fixed-price workflow, if opportunities convert.
These are operational goals, not guarantees or evidence of contracts.

## Host / model governance
Ace Magic mini PC: CPU/RAM/SSD/virtualization/tailnet details UNKNOWN until Zane read-only probe. Primary HQ/DB/control candidate, not automatic GPU. Tiny transformer: quantized Qwen/Phi class only if measured RAM permits; medium/large transformers use qualified remote resources and verified free entitlements or separately approved spending; never pretend combined RAM is shared memory. Data stack: small start SQLite + append-only job evidence; consider PostgreSQL/pgvector + DuckDB later, not ten redundant DBs. Resilience: backup tested, STOP switch, one-heavy-worker on constrained nodes, admission and quota checks; encrypted identity grants by trusted broker.
No hosted service, external outreach, paid route, provider sign-in or production account creation has occurred by this RFC.

## Release gates (never skip)
S0 code audit; P0 finance denial patch + tests; E0 real mini PC and provider inventory; E1 offline MCP fixture/policy tests; E2 safe StarNet/Agent X adapter; P1 sandbox processor proof + exactly-once fulfillment + journal balance + webhook tamper/fraud tests; P2 independent security review including multi-tenant access and prompt injection; P3 provider/legal/PCI scope/terms review; P4 owner-approved real pilot; P5 72h measured stability + reconciled payments before any wider release.

## Existing related artifacts
- Genesis Mission Ledger and `operator_continuity.py`, Success Loop draft PR #79: https://github.com/brandonduda8/astra-zane-bridge/pull/79
- Agent X guarded queue PR #5: https://github.com/brandonduda8/Agent-x/pull/5
- Genesis Key Vault proof PR #6: https://github.com/brandonduda8/Agent-x/pull/6
- Cody STEM/YOLO lab PR #7/8 (Agent-x), HQ work order #80, contract order #85
- Genesis Pay prior Argon work order: https://github.com/brandonduda8/astra-zane-bridge/blob/main/shared/genesis-pay/20261020T161505Z-argon-enterprise-payments-and-business-intelligence-work-order.md
- Google AP2: https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/
- PCI SSC: https://www.pcisecuritystandards.org/standards/pci-dss/
- Coinbase x402 MCP docs: https://docs.cdp.coinbase.com/api-reference/v2/rest-api/x402-facilitator/bazaar-mcp-server

## Responsibility
Cody — code/QA model and MCP tools in isolated branch; Claude — independent engineering security review; Zane — read-only live host/credential entitlement (never secret values), private deployment design; Astra — vendor/protocol research and risk; Themis/QA — independent end-to-end proof; Brandon — approvals for entity/processor onboarding, customer data, real spending, client submissions, signing and releases.

**Important:** client/provider identity verification, banking onboarding, contracts, and any regulated payment activities cannot be silently skipped just to avoid owner setup. Minimize these owner tasks and batch them in one approval desk.
