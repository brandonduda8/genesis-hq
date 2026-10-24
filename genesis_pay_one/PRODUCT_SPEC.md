# Genesis Pay ONE | Spend, Protect, Invest

**Created:** 2026-10-24 | **Status:** R&D PROTOTYPE ONLY | **Real card issued:** NO | **Real money moved:** $0

## Promise and distinction

ONE card should eventually combine a simple everyday checking/debit experience with clear credit-like features and automatic, user-authorized micro-investing. The minimum useful product is a deterministic spending/round-up planning app that works with *existing partner accounts* instead of acting as a bank, lender or broker. The long-term differentiator is an independent AI financial assistant that helps users set limits, maintain reserves, manage bills, understand investments and control the spending authority of AI agents.

Debit is not credit. Using the network's credit checkout path does not make a debit transaction a loan or report a credit history. True credit-building requires an appropriate lending/secured credit agreement, lending partner, credit bureau reporting and relevant disclosures. A single flexible credential is possible in some partner programs (Visa Flexible Credential), not something the Genesis app can activate by itself.

## Product slices

| Phase | Product capability | Capability owner | Limits |
| --- | --- | --- | --- |
| 0 | Wallet/card interface, settled-purchase round-ups, simulated portfolios, reserve and refund controls | Genesis local app and Cody | Only synthetic fixtures, no bank API |
| 1 | Read-only external bank transaction connection, categorization, round-up **drafts** | User-approved banking/open-finance provider; financial data agreement | No transfers, confirmed customer identity, minimize PII |
| 2 | Authorized brokerage micro-investing and cash sweeps | Approved brokerage partner; consumer funds held by partners | KYC, funding, fractional eligibility, taxes, securities compliance, explicit investment consent |
| 3 | Branded virtual/physical debit card and account features | Issuer bank + licensed issuing/processing partner | Sponsorship, BIN, network/marketing approvals, CIP/KYC/AML, servicing, complaints, fraud, chargebacks, contracts |
| 4 | Flexible debit/credit or secured line, credit bureau reporting | Issuer/lender + network-supported credential service | Underwriting, credit agreements, Reg Z/Reg E and reporting controls |
| 5 | Agent purchase mandates and premium multi-tenant platform | Genesis Pay + licensed payment partners | Revocable scoped authorization, never AI self-approval |

### Candidate commercial partners (not under contract)

- Issuing/processors to compare: Stripe Issuing (consumer+business features subject to program approval), Marqeta (Flexible Credentials and debit/credit), Lithic (issuing/program management and sandbox). Current fee sheets, eligibility and bank availability: UNKNOWN.
- Brokerage services: Alpaca Broker API/Connect and DriveWealth API for fractional securities, account opening and funding. Their integrations are not authorized, and commercial eligibility/fees: UNKNOWN.
- Deposit/investment reconciliation must come from actual bank/broker/processor evidence. Store no PAN, CVV, bank passwords, or broker tokens in Genesis prompts or model memory.

## Round-ups exact arithmetic and controls

- Only *settled* eligible debit purchases count, never card authorization holds or declined/voided transactions.
- Compute in integer minor currency units (USD cents): `(100 - purchase_cents % 100) % 100`. `$7.35 => $0.65`, `$12.10 => $0.90`, `$20.00 => $0.00`.
- Add to a *proposed accrual*, not to a fake account balance. Source account stays at issuer bank.
- Refund/dispute/chargeback: quarantine that purchase's accrual for reconciliation. If investment already occurred in future, don't automatically sell positions based on an unverified refund.
- Default roundup OFF until affirmative customer opt-in, require separately chosen portfolio weights and permitted investments. Never silently select stocks or securities.
- Default batch minimum $5 (configurable); enforce emergency cash reserve ($50 in the demo), daily/monthly user caps, fees and minimum trade quantities, broker eligibility and allowed funding windows. If short on cash, pause; never overdraft for investing.
- A future live system would add per-account event idempotency, signed provider events, original transaction matching, clearing/settlement timing, concurrency-safe financial journal, reproducible failover, AML/fraud monitoring and held-cash reconciliation. The demo is explicitly not that system.
- Real investment results may rise or fall; stocks and ETFs are NOT FDIC-insured deposits. Model portfolio allocations must be initiated by user selection or legally authorized investment adviser/broker instructions, not open-ended LLM discretion.

## Personal and business boundaries

Personal roundup portfolio != Genesis company's operating account or card. Maintain separate legal ownership, accounting records, bank/broker permissions and agent mandates. Owner budgets for agents apply only to authorized business purchases, not personal investing. Do not automatically sweep company income to a personal brokerage account.

## Intelligent features to build in order

1. Deterministic budgeting: balances, reserves, bills, cash runway; alert before overdraft or insufficient available funds.
2. Source-grounded financial coach: spending classification, recurring subscription alerts, explicit opt-in goals. AI may explain and suggest, never move funds or guarantee returns.
3. Portfolio explorer: contribution history, fees, asset mix, risk and tax-lot disclosures from brokerage data; portfolio performance clearly separated from contributed principal.
4. Merchant controls: lock/unlock, category/merchant/geography/velocity limits implemented by issuer where supported; deny/allow in trusted payment control plane, not prompt decisions.
5. Optional rewards: actual partner-funded cashback or merchant offers with a proven budget. Interchange must cover bank/processor/network cost, fraud, rewards, compliance, servicing; no mythical 'money from nothing'.
6. Secured credit-builder: add only with a lending partner and accurate reporting; avoid misleading 'debit builds credit' claims.
7. Agent purchases: spend request -> customer mandate -> independent policy verifier -> partner payment -> event+settlement reconciliation; deny self-approval.

## Legal, safety and revenue gates

The issuer, lending partner and brokerage must run legally authorized programs. Consumer protection obligations may include Reg E, Reg Z, BSA/AML, KYC/CIP, data security, fair lending, disputes, state licensing and investment-adviser rules, depending on structure and operation. Fintech software alone provides none of these licenses. Investment funds are not FDIC insured and may lose value. Legal and provider program review before any live product.

Business model candidates: optional clearly priced subscription for verified coaching, merchant-funded rewards, B2B licensing of analytics, and disclosed partner revenue arrangements if legally permitted. Early service fees must not overwhelm micro-investing amounts. No guarantee of profit or credit score gain.

## Real next steps for Zane / Cody / Alliance

1. Review existing Genesis-core payment freeze PR #4 and complete independent security audit; don't connect bad rails.
2. Run this engine's test suite and inspect its demo UI. Fix defects without attaching real banking credentials.
3. Audit issuer, broker and banking partnerships for actual availability, fee sheets, credit product eligibility, supported consumer program, responsible entities and contract terms.
4. Get a sample sandbox card lifecycle event and broker sandbox fractional-notional example under a separately authorized test; then build replay-safe adapter and reconciliation fixtures.
5. Deliver an owner-review package with partner costs, legal gate, honest milestones, brand constraints and simulated use cases. No automatic accounts or new spend.

## Official source references (review current versions before integration)

- Visa Flexible Credential https://www.visa.com/en-us/products/flex-credential
- Marqeta Flexible Credentials https://www.marqeta.com/platform/flexible-credentials
- Stripe Issuing https://stripe.com/issuing
- Lithic sandbox documentation https://docs.lithic.com/
- Alpaca Broker API https://docs.alpaca.markets/us/docs/getting-started-with-broker-api
- DriveWealth API https://developer.drivewealth.com/apis/docs/intro
- Acorns Round-ups (product comparison) https://www.acorns.com/round-ups/
- CFPB debit vs credit https://www.consumerfinance.gov/ask-cfpb/how-are-prepaid-cards-debit-cards-and-credit-cards-different-en-433/
- CFPB credit building https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/how-to-rebuild-your-credit/
- FDIC fintech apps https://www.fdic.gov/consumer-resource-center/2024-06/banking-third-party-apps
- SEC robo-adviser considerations https://www.sec.gov/news/press-release/2017-52
