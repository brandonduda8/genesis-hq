# Genesis Foundry — Product and Value Charter (October 9, 2026)

## Mission
Help individuals and small teams turn a real business problem into a useful, portable software tool. Users should own their code and data and receive reproducible evidence of what works.

Promise to test: "Describe the tool your business needs. Receive a working app, its source code, and a verification report."

Hugging Face is an ecosystem inspiration: free building blocks enable broad adoption; organizations can pay for supported, private, governed services. Genesis must earn customer trust and repeat usage, not assume either.

## First customer and application
Initial segment: owner-operated service businesses and small agencies who lose leads and waste effort preparing quotes in disconnected spreadsheets and inboxes.

First sellable showcase: Lead-to-Quote Workspace, dogfooded on the owner's Apex workflow with synthetic data. Minimum real app:
1. Capture a fictional lead into an intake list.
2. Persist and update stages, notes, owner, and a quote draft.
3. Filter/search entries and export CSV/JSON.
4. Run locally with documented setup and an actual persistent database, surviving restart.
5. Enforce authorization when remotely accessible; never send messages or move money without approval.
6. Include tested installation, backup, rollback, export and an independent verification report.

Foundry v0.1 website generation is a genuine exportable prototype, not yet an AI software factory or a priced core product.

## Product layers
- Genesis Foundry: problem -> accepted specification -> versioned recipe -> portable software artifact.
- Genesis Hub: public recipes and templates with tests, licenses, reproducibility and honest ratings.
- Genesis Ledger: one authoritative job queue, approvals, failure/retry limits and evidence.
- Phoenix HQ: accessible status, approvals, artifact downloads and proof.
- Ruflo: task coordination only; verified builders and independent reviewers perform actual work.
- Host: owner-controlled deployments first. Render Free may host a demo, not be trusted as persistent worker/storage.

Every shipped package includes source, dependency/license manifest, sample data, runtime constraints, tests, output hashes, install/rollback notes, data export and actual executor/reviewer evidence. Proposed and simulated work never counts as autonomous execution.

## Business model hypotheses
- Free: starter recipes, local demos, public documentation, reusable templates.
- Paid implementation: fixed-scope customization and setup, testing a range of $300–$1,000 only after requirements and delivery costs are measured.
- Managed Teams: private recipes, governed workers, shared history and monitoring; test $79–$299/month only after interviews and cost modeling.
- Later enterprise: dedicated deployment, permissioned integrations, audit and support priced individually.

No paid service is offered before a working deliverable, support plan and owner-approved checkout. Each pilot has a compute/hosting/support budget and contribution margin. No unverified "free" inference capacity may be used to subsidize paid customers.

## October 9–11 proof sprint
Friday: benchmark v0.1, create Lead-to-Quote feature spec and sample data, begin actual data persistence and CRUD.
Saturday: implement quote building and export; test invalid inputs, duplicate jobs, restart, cancellation and safe permissions; capture real desktop/mobile QA if tooling works.
Sunday: independent reviewer repeats clean-checkout tests, verify output hashes, record an accurate 60–90 second demo, prepare release candidate and customer interview script. No outreach or publication without owner approval.

Definition of done: a new user can create a lead, draft a quote and export its data without coding. Tests, reviewer and deployment evidence are attached. An appealing UI alone does not pass.

## Alliance execution
Zane: verify current workers, available quotas, Render and host capacity. Claude: isolated builder. OpenHands and Antigravity: candidate workers only after verified tools and $0 allowance. Ruflo: dependency planning; no second job authority. Separate reviewer: replay tests and check claims. Product lane: package demo and interview questions, never silently publish or contact customers.

Rules: $0 incremental cost; no production, publishing, outreach, model spending, private customer data, or payments without explicit owner permission; licenses and sources retained.

Engineering tracker: https://github.com/brandonduda8/astra-zane-bridge/issues/6
